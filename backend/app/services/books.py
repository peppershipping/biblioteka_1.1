"""
Каталог: создание книг, полнотекстовый вектор, поиск и фильтрация.

Поиск (ТЗ 4.3): PostgreSQL Full-Text Search по search_vector (GIN-индекс) —
название, авторы, жанры, описание; плюс подстрочное совпадение в названии и
имени автора, чтобы находились неполные слова («булг» -> «Булгаков»).
"""

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from ..models import Author, Book, Genre, Rating, UserBook


class DuplicateBookError(Exception):
    """Книга с таким названием и авторами уже есть в каталоге."""


def like_pattern(value: str) -> str:
    """Экранирует служебные символы LIKE (% _ \\) в пользовательском вводе."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


_REFRESH_VECTOR_SQL = text(
    """
    UPDATE books SET search_vector =
        setweight(to_tsvector('russian', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('russian', coalesce((
            SELECT string_agg(a.name, ' ') FROM book_authors ba
            JOIN authors a ON a.id = ba.author_id WHERE ba.book_id = books.id), '')), 'B') ||
        setweight(to_tsvector('russian', coalesce((
            SELECT string_agg(g.name, ' ') FROM book_genres bg
            JOIN genres g ON g.id = bg.genre_id WHERE bg.book_id = books.id), '')), 'B') ||
        setweight(to_tsvector('russian', coalesce(description, '')), 'C')
    WHERE id = :book_id
    """
)


def refresh_search_vector(db: Session, book_id: int) -> None:
    db.execute(_REFRESH_VECTOR_SQL, {"book_id": book_id})


def _get_or_create(db: Session, model, names: list[str]) -> list:
    result = []
    for name in names:
        obj = db.scalar(select(model).where(func.lower(model.name) == name.lower()))
        if obj is None:
            obj = model(name=name)
            db.add(obj)
            db.flush()
        result.append(obj)
    return result


def create_book(
    db: Session,
    *,
    title: str,
    description: str | None = None,
    publication_year: int | None = None,
    cover_url: str | None = None,
    authors: list[str] | None = None,
    genres: list[str] | None = None,
) -> Book:
    """Создаёт книгу вместе с авторами/жанрами; транзакцию фиксирует вызывающий код."""
    authors = authors or []
    wanted_authors = {a.lower() for a in authors}
    same_title = db.scalars(
        select(Book).where(func.lower(Book.title) == title.lower()).options(selectinload(Book.authors))
    ).all()
    for existing in same_title:
        if {a.name.lower() for a in existing.authors} == wanted_authors:
            raise DuplicateBookError()

    book = Book(title=title, description=description, publication_year=publication_year, cover_url=cover_url)
    book.authors = _get_or_create(db, Author, authors)
    book.genres = _get_or_create(db, Genre, genres or [])
    db.add(book)
    db.flush()
    refresh_search_vector(db, book.id)
    return book


def search_books(
    db: Session,
    *,
    q: str | None = None,
    genre: str | None = None,
    author: str | None = None,
    year: int | None = None,
    sort: str | None = None,
    order: str = "asc",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Book], int]:
    """Возвращает (книги страницы, общее число найденных). sort — из белого списка."""
    filters = []
    relevance = None
    if q:
        tsquery = func.websearch_to_tsquery("russian", q)
        pattern = like_pattern(q)
        filters.append(
            or_(
                Book.search_vector.op("@@")(tsquery),
                Book.title.ilike(pattern, escape="\\"),
                Book.authors.any(Author.name.ilike(pattern, escape="\\")),
            )
        )
        relevance = func.ts_rank(Book.search_vector, tsquery)
    if genre:
        filters.append(Book.genres.any(func.lower(Genre.name) == genre.lower()))
    if author:
        filters.append(Book.authors.any(Author.name.ilike(like_pattern(author), escape="\\")))
    if year is not None:
        filters.append(Book.publication_year == year)

    total = db.scalar(select(func.count()).select_from(Book).where(*filters)) or 0

    if sort in (None, "relevance") and relevance is not None:
        ordering = [relevance.desc(), func.lower(Book.title), Book.id]
    else:
        columns = {"title": func.lower(Book.title), "year": Book.publication_year, "created": Book.created_at}
        column = columns.get(sort or "title", columns["title"])
        direction = column.desc() if order == "desc" else column.asc()
        if sort == "year":
            direction = direction.nulls_last()
        ordering = [direction, Book.id]

    books = db.scalars(
        select(Book)
        .where(*filters)
        .options(selectinload(Book.authors), selectinload(Book.genres))
        .order_by(*ordering)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(books), total


def user_overlay(db: Session, user_id: int | None, book_ids: list[int]) -> dict[int, tuple]:
    """{book_id: (статус, итоговая оценка | None)} для книг из библиотеки пользователя."""
    if user_id is None or not book_ids:
        return {}
    rows = db.execute(
        select(UserBook.book_id, UserBook.status, Rating.total)
        .outerjoin(Rating, Rating.user_book_id == UserBook.id)
        .where(UserBook.user_id == user_id, UserBook.book_id.in_(book_ids))
    ).all()
    return {book_id: (status, float(total) if total is not None else None) for book_id, status, total in rows}


def rating_summary(db: Session, book_id: int) -> tuple[float | None, int]:
    """(средняя итоговая оценка всех пользователей, число оценок)."""
    avg, count = db.execute(
        select(func.avg(Rating.total), func.count(Rating.id))
        .join(UserBook, UserBook.id == Rating.user_book_id)
        .where(UserBook.book_id == book_id)
    ).one()
    return (round(float(avg), 1) if avg is not None else None), int(count)
