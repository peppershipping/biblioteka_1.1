<<<<<<< HEAD
"""
Оценки (ТЗ 4.2, 8, 15.1, 17).

Правила: оценка создаётся только для книги из личной библиотеки текущего
пользователя и только при статусе «Прочитано»; критерии — целые 1..10;
total = среднее трёх критериев (округление до одного знака), пересчитывается
при создании и изменении. Изменения оценок попадают в rating_audit
(changed_by заполняется из app.current_user_id).
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..models import Book, Rating, ReadingStatus, User, UserBook
from ..ratelimit import DefaultLimit
from ..schemas import Page, PublicRatingOut, RatingIn, RatingOut, RatingPatch
from ..services import recommender
from ..services.ratings import compute_total

router = APIRouter(tags=["Оценки"], dependencies=[DefaultLimit])

NOT_IN_LIBRARY = "Книга не найдена в вашей библиотеке"
NOT_READ = "Оценивать можно только книги со статусом «Прочитано»"


def _entry(db: Session, user_id: int, book_id: int) -> UserBook:
    entry = db.scalar(
        select(UserBook)
        .where(UserBook.user_id == user_id, UserBook.book_id == book_id)
        .options(selectinload(UserBook.rating))
    )
    if entry is None:
        raise HTTPException(404, NOT_IN_LIBRARY)
    return entry


def _require_read(entry: UserBook) -> None:
    if entry.status != ReadingStatus.read:
        raise HTTPException(409, NOT_READ)


def _audit_user(db: Session, user_id: int) -> None:
    """Передаёт id пользователя триггеру аудита (переменная действует до конца транзакции)."""
    db.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(user_id)})


def _out(rating: Rating, book_id: int) -> RatingOut:
    return RatingOut(
        book_id=book_id,
        plot=rating.plot,
        characters=rating.characters,
        style=rating.style,
        total=rating.total,
        updated_at=rating.updated_at,
    )


def _save(db: Session, user_id: int, entry: UserBook) -> None:
    try:
        db.commit()
    except IntegrityError:  # одновременное создание второй оценки: UNIQUE (user_book_id)
        db.rollback()
        raise HTTPException(409, "Оценка этой книги уже существует")
    db.refresh(entry.rating)  # подтягиваем total и updated_at, посчитанные триггером БД
    recommender.invalidate(user_id)


@router.get("/books/{book_id}/rating", response_model=RatingOut, summary="Моя оценка книги")
def get_my_rating(book_id: int = Path(ge=1), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = _entry(db, user.id, book_id)
    if entry.rating is None:
        raise HTTPException(404, "Вы ещё не оценивали эту книгу")
    return _out(entry.rating, book_id)


@router.post("/books/{book_id}/rating", response_model=RatingOut, status_code=201, summary="Создать (или заменить) мою оценку")
def put_rating(
    payload: RatingIn,
    response: Response,
    book_id: int = Path(ge=1),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """201 — оценка создана, 200 — существующая оценка обновлена."""
    entry = _entry(db, user.id, book_id)
    _require_read(entry)
    _audit_user(db, user.id)
    total = compute_total(payload.plot, payload.characters, payload.style)
    if entry.rating is None:
        entry.rating = Rating(plot=payload.plot, characters=payload.characters, style=payload.style, total=total)
    else:
        response.status_code = 200
        entry.rating.plot, entry.rating.characters, entry.rating.style = payload.plot, payload.characters, payload.style
        entry.rating.total = total
    _save(db, user.id, entry)
    return _out(entry.rating, book_id)


@router.patch("/books/{book_id}/rating", response_model=RatingOut, summary="Изменить критерии моей оценки")
def patch_rating(
    payload: RatingPatch,
    book_id: int = Path(ge=1),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _entry(db, user.id, book_id)
    _require_read(entry)
    rating = entry.rating
    if rating is None:
        raise HTTPException(404, "Оценка ещё не создана — используйте POST")
    _audit_user(db, user.id)
    for field in ("plot", "characters", "style"):
        value = getattr(payload, field)
        if value is not None:
            setattr(rating, field, value)
    rating.total = compute_total(rating.plot, rating.characters, rating.style)
    _save(db, user.id, entry)
    return _out(rating, book_id)


@router.get("/books/{book_id}/ratings", response_model=Page[PublicRatingOut], summary="Все оценки книги")
def list_book_ratings(
    book_id: int = Path(ge=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    if db.get(Book, book_id) is None:
        raise HTTPException(404, "Книга не найдена")
    base = (
        select(Rating, User.username)
        .join(UserBook, UserBook.id == Rating.user_book_id)
        .join(User, User.id == UserBook.user_id)
        .where(UserBook.book_id == book_id)
    )
    total = db.scalar(
        select(func.count(Rating.id)).join(UserBook, UserBook.id == Rating.user_book_id).where(UserBook.book_id == book_id)
    ) or 0
    rows = db.execute(base.order_by(Rating.updated_at.desc(), Rating.id.desc()).limit(limit).offset(offset)).all()
    items = [
        PublicRatingOut(
            username=username,
            plot=r.plot,
            characters=r.characters,
            style=r.style,
            total=r.total,
            updated_at=r.updated_at,
        )
        for r, username in rows
    ]
    return {"items": items, "limit": limit, "offset": offset, "total": total}
=======
"""Многокритериальные оценки: сюжет, персонажи, стиль → итог = среднее трёх."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/library", tags=["ratings"])


def _get_entry(db: Session, user: models.User, entry_id: int) -> models.UserBook:
    entry = db.scalar(
        select(models.UserBook).where(
            models.UserBook.id == entry_id, models.UserBook.user_id == user.id
        )
    )
    if entry is None:
        raise HTTPException(404, detail={"code": "not_found", "message": "Запись не найдена."})
    return entry


@router.get("/{entry_id}/rating", response_model=schemas.RatingOut)
def get_rating(
    entry_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    entry = _get_entry(db, user, entry_id)
    if entry.rating is None:
        raise HTTPException(404, detail={"code": "not_found", "message": "Оценка ещё не выставлена."})
    return entry.rating


@router.put("/{entry_id}/rating", response_model=schemas.RatingOut)
def put_rating(
    entry_id: int,
    payload: schemas.RatingIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    entry = _get_entry(db, user, entry_id)
    total = round((payload.plot + payload.characters + payload.style) / 3, 2)

    if entry.rating is None:
        entry.rating = models.Rating(
            plot=payload.plot, characters=payload.characters, style=payload.style, total=total
        )
    else:
        entry.rating.plot = payload.plot
        entry.rating.characters = payload.characters
        entry.rating.style = payload.style
        entry.rating.total = total

    # Оценённая книга считается прочитанной
    entry.status = "read"
    db.commit()
    db.refresh(entry.rating)
    return entry.rating


@router.delete("/{entry_id}/rating")
def delete_rating(
    entry_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    entry = _get_entry(db, user, entry_id)
    if entry.rating is None:
        raise HTTPException(404, detail={"code": "not_found", "message": "Оценка ещё не выставлена."})
    db.delete(entry.rating)
    db.commit()
    return {"detail": "Оценка удалена."}
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
