"""
Рекомендации: работа с БД вокруг чистого ядра recommender_engine.

Правила ТЗ:
  * персональная подборка — только при >= 3 оценок (правило 34); до этого —
    сообщение и неперсональная подборка «популярное»;
  * книги из библиотеки пользователя не рекомендуются (правило 35);
  * книги с обратной связью «не полезно» больше не предлагаются;
  * сбой языковой модели не блокирует подбор (правило 37) — пояснения просто
    отсутствуют;
  * результаты кэшируются в Redis на 1 час, ключ включает версию профиля
    пользователя (инвалидация — services.recommender.invalidate).
"""

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from .. import cache, models
from ..config import get_settings
from ..models import Author, Book, Genre, Rating, Recommendation, UserBook
from ..schemas import BookOut, RecommendationOut, RecommendationSignals
from . import llm
from .recommender_engine import BookDoc, profile_weight, rank

MIN_RATINGS = 3
CANDIDATE_CAP = 3000   # верхняя граница пула кандидатов для TF-IDF (масштаб до 100 000 книг)
FRESH_BOOKS = 200      # свежие книги добавляются в пул для разнообразия
RANKING_LIMIT = 100


def invalidate(user_id: int) -> None:
    """Вызывать при изменении оценок, статусов, библиотеки или обратной связи пользователя."""
    cache.bump(f"user:{user_id}")


def count_ratings(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count(Rating.id))
        .join(UserBook, UserBook.id == Rating.user_book_id)
        .where(UserBook.user_id == user_id)
    ) or 0


def _excluded_ids(db: Session, user_id: int) -> set[int]:
    in_library = db.scalars(select(UserBook.book_id).where(UserBook.user_id == user_id)).all()
    rejected = db.scalars(
        select(Recommendation.book_id).where(
            Recommendation.user_id == user_id, Recommendation.feedback == models.FEEDBACK_NOT_HELPFUL
        )
    ).all()
    return set(in_library) | set(rejected)


def _doc(book: Book) -> BookDoc:
    return BookDoc(
        id=book.id,
        title=book.title,
        description=book.description or "",
        authors=[a.name for a in book.authors],
        genres=[g.name for g in book.genres],
    )


def _load_profile(db: Session, user_id: int) -> list[tuple[Book, float]]:
    entries = db.scalars(
        select(UserBook)
        .join(UserBook.rating)
        .where(UserBook.user_id == user_id)
        .options(
            selectinload(UserBook.rating),
            selectinload(UserBook.book).selectinload(Book.authors),
            selectinload(UserBook.book).selectinload(Book.genres),
        )
    ).all()
    return [(e.book, profile_weight(float(e.rating.total))) for e in entries]


def _candidates(db: Session, liked: list[Book], excluded: set[int]) -> list[Book]:
    genre_ids = {g.id for b in liked for g in b.genres}
    author_ids = {a.id for b in liked for a in b.authors}
    conditions = []
    if genre_ids:
        conditions.append(Book.genres.any(Genre.id.in_(genre_ids)))
    if author_ids:
        conditions.append(Book.authors.any(Author.id.in_(author_ids)))

    def query(*where):
        stmt = select(Book).options(selectinload(Book.authors), selectinload(Book.genres))
        if excluded:
            stmt = stmt.where(Book.id.not_in(excluded))
        return stmt.where(*where)

    pool: dict[int, Book] = {}
    if conditions:
        for b in db.scalars(query(or_(*conditions)).order_by(Book.id.desc()).limit(CANDIDATE_CAP)):
            pool[b.id] = b
    for b in db.scalars(query().order_by(Book.created_at.desc(), Book.id.desc()).limit(FRESH_BOOKS)):
        pool.setdefault(b.id, b)
    return list(pool.values())


def _personalized_ranking(db: Session, user_id: int) -> list[dict]:
    profile_books = _load_profile(db, user_id)
    profile = [(_doc(b), w) for b, w in profile_books if w != 0]
    liked_books = [b for b, w in profile_books if w > 0]
    if not liked_books:
        return []
    candidates = [_doc(b) for b in _candidates(db, liked_books, _excluded_ids(db, user_id))]
    titles = {d.id: d.title for d, _ in profile}
    return [
        {
            "book_id": r.book_id,
            "score": r.score,
            "similar_to": titles.get(r.similar_to_id),
            "genres": r.shared_genres,
        }
        for r in rank(candidates, profile, RANKING_LIMIT)
    ]


def _popular_ranking(db: Session, user_id: int) -> list[dict]:
    """Неперсональная подборка: книги с лучшими средними оценками, затем новинки."""
    excluded = _excluded_ids(db, user_id)
    avg = func.avg(Rating.total)
    stmt = (
        select(Book.id)
        .join(UserBook, UserBook.book_id == Book.id)
        .join(Rating, Rating.user_book_id == UserBook.id)
        .group_by(Book.id)
        .order_by(avg.desc(), func.count(Rating.id).desc(), Book.id)
        .limit(RANKING_LIMIT)
    )
    if excluded:
        stmt = stmt.where(Book.id.not_in(excluded))
    ids = list(db.scalars(stmt))
    if len(ids) < RANKING_LIMIT:
        fresh = select(Book.id).order_by(Book.created_at.desc(), Book.id.desc()).limit(RANKING_LIMIT)
        skip = excluded | set(ids)
        if skip:
            fresh = fresh.where(Book.id.not_in(skip))
        ids += list(db.scalars(fresh))[: RANKING_LIMIT - len(ids)]
    return [{"book_id": i, "score": None, "similar_to": None, "genres": []} for i in ids]


def _ranking(db: Session, user_id: int, personalized: bool) -> list[dict]:
    key = f"reco:{user_id}:v{cache.version(f'user:{user_id}')}:{'p' if personalized else 'n'}"
    cached = cache.get_json(key)
    if cached is not None:
        return cached
    items = _personalized_ranking(db, user_id) if personalized else _popular_ranking(db, user_id)
    cache.set_json(key, items, get_settings().cache_recommendations_ttl)
    return items


def _liked_titles(db: Session, user_id: int, limit: int = 5) -> list[str]:
    return list(
        db.scalars(
            select(Book.title)
            .join(UserBook, UserBook.book_id == Book.id)
            .join(Rating, Rating.user_book_id == UserBook.id)
            .where(UserBook.user_id == user_id, Rating.total >= 7)
            .order_by(Rating.total.desc(), Rating.updated_at.desc())
            .limit(limit)
        )
    )


def _upsert_rows(db: Session, user_id: int, book_ids: list[int]) -> dict[int, Recommendation]:
    if not book_ids:
        return {}
    db.execute(
        pg_insert(Recommendation)
        .values([{"user_id": user_id, "book_id": b} for b in book_ids])
        .on_conflict_do_nothing(index_elements=["user_id", "book_id"])
    )
    rows = db.scalars(
        select(Recommendation).where(Recommendation.user_id == user_id, Recommendation.book_id.in_(book_ids))
    ).all()
    db.commit()
    return {r.book_id: r for r in rows}


def build_page(db: Session, user: models.User, limit: int, offset: int) -> dict:
    """Собирает ответ GET /recommendations."""
    ratings = count_ratings(db, user.id)
    personalized = ratings >= MIN_RATINGS
    message = None

    ranking = _ranking(db, user.id, personalized)
    if personalized and not ranking:
        personalized = False
        ranking = _ranking(db, user.id, False)
        message = "Пока не нашлось книг, похожих на ваши оценки, — показаны популярные."
    elif not personalized:
        message = (
            f"Персональные рекомендации появятся после трёх оценок (сейчас: {ratings}). "
            "Пока показываем популярные книги."
        )

    page = ranking[offset : offset + limit]
    ids = [it["book_id"] for it in page]
    books = {
        b.id: b
        for b in db.scalars(
            select(Book).where(Book.id.in_(ids)).options(selectinload(Book.authors), selectinload(Book.genres))
        )
    } if ids else {}
    page = [it for it in page if it["book_id"] in books]  # книга могла быть удалена после кэширования
    rows = _upsert_rows(db, user.id, [it["book_id"] for it in page])

    # Пояснения языковой модели — только для персональной подборки и только для
    # тех строк, где пояснения ещё нет (результат сохраняется в БД: повторных затрат нет).
    if personalized and get_settings().llm_enabled:
        need = [it for it in page if rows[it["book_id"]].reason is None]
        if need:
            reasons = llm.explain(
                _liked_titles(db, user.id),
                [
                    {
                        "book_id": it["book_id"],
                        "title": books[it["book_id"]].title,
                        "authors": [a.name for a in books[it["book_id"]].authors],
                        "genres": [g.name for g in books[it["book_id"]].genres],
                        "similar_to": it["similar_to"],
                    }
                    for it in need
                ],
            )
            if reasons:
                for book_id, text in reasons.items():
                    rows[book_id].reason = text
                db.commit()

    items = [
        RecommendationOut(
            id=rows[it["book_id"]].id,
            book=BookOut.model_validate(books[it["book_id"]]),
            reason=rows[it["book_id"]].reason,
            score=it["score"],
            signals=RecommendationSignals(similar_to=it["similar_to"], genres=it["genres"]),
            feedback=rows[it["book_id"]].feedback,
        )
        for it in page
    ]
    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "total": len(ranking),
        "personalized": personalized,
        "ratings_count": ratings,
        "min_ratings": MIN_RATINGS,
        "message": message,
        "explanations": any(i.reason for i in items),
    }
