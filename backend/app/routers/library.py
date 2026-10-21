"""Личная библиотека пользователя: список, добавление (из поиска или вручную), статус, комментарий, удаление."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/library", tags=["library"])


def _not_found():
    return HTTPException(404, detail={"code": "not_found", "message": "Запись не найдена."})


def _to_out(entry: models.UserBook) -> schemas.UserBookOut:
    out = schemas.UserBookOut.model_validate(entry)
    out.my_rating = entry.rating.total if entry.rating else None
    return out


def _load_entry(db: Session, user: models.User, entry_id: int) -> models.UserBook:
    entry = db.scalar(
        select(models.UserBook)
        .options(
            selectinload(models.UserBook.book).selectinload(models.Book.authors),
            selectinload(models.UserBook.book).selectinload(models.Book.genres),
            selectinload(models.UserBook.rating),
        )
        .where(models.UserBook.id == entry_id, models.UserBook.user_id == user.id)
    )
    if entry is None:
        # чужая запись неотличима от несуществующей
        raise _not_found()
    return entry


@router.get("", response_model=list[schemas.UserBookOut])
def list_library(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    stmt = (
        select(models.UserBook)
        .options(
            selectinload(models.UserBook.book).selectinload(models.Book.authors),
            selectinload(models.UserBook.book).selectinload(models.Book.genres),
            selectinload(models.UserBook.rating),
        )
        .where(models.UserBook.user_id == user.id)
        .order_by(models.UserBook.added_at.desc())
    )
    if status:
        if status not in schemas.VALID_STATUSES:
            raise HTTPException(400, detail={"code": "validation_error", "message": "Недопустимый статус."})
        stmt = stmt.where(models.UserBook.status == status)
    return [_to_out(e) for e in db.scalars(stmt).all()]


@router.post("", response_model=schemas.UserBookOut, status_code=201)
def add_to_library(
    payload: schemas.UserBookCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if db.get(models.Book, payload.book_id) is None:
        raise HTTPException(404, detail={"code": "not_found", "message": "Книга не найдена."})

    existing = db.scalar(
        select(models.UserBook).where(
            models.UserBook.user_id == user.id, models.UserBook.book_id == payload.book_id
        )
    )
    if existing:
        raise HTTPException(
            409, detail={"code": "conflict", "message": "Книга уже есть в вашей библиотеке."}
        )

    entry = models.UserBook(user_id=user.id, book_id=payload.book_id, status=payload.status)
    db.add(entry)
    db.commit()
    return _to_out(_load_entry(db, user, entry.id))


@router.post("/custom", response_model=schemas.UserBookOut, status_code=201)
def add_custom_book(
    payload: schemas.CustomBookCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    Форма «Добавить книгу»: название, автор, краткое описание сюжета, комментарий.
    Если в общей базе уже есть книга с таким названием и автором — берём её
    (так «каталог» постепенно наполняется сам и находится через поиск),
    иначе создаём новую. Комментарий — личный, хранится в записи библиотеки.
    """
    title = payload.title.strip()
    author_name = payload.author.strip()
    if not title or not author_name:
        raise HTTPException(
            400, detail={"code": "validation_error", "message": "Укажите название и автора."}
        )

    book = db.scalar(
        select(models.Book)
        .join(models.Book.authors)
        .where(
            func.lower(models.Book.title) == title.lower(),
            func.lower(models.Author.name) == author_name.lower(),
        )
    )

    if book is None:
        author = db.scalar(select(models.Author).where(func.lower(models.Author.name) == author_name.lower()))
        if author is None:
            author = models.Author(name=author_name)
            db.add(author)
            db.flush()
        book = models.Book(title=title, description=payload.description.strip(), keywords="")
        book.authors = [author]
        db.add(book)
        db.flush()

    existing = db.scalar(
        select(models.UserBook).where(
            models.UserBook.user_id == user.id, models.UserBook.book_id == book.id
        )
    )
    if existing:
        raise HTTPException(
            409, detail={"code": "conflict", "message": "Эта книга уже есть в вашей библиотеке."}
        )

    entry = models.UserBook(
        user_id=user.id,
        book_id=book.id,
        status=models.UserBook.STATUS_WANT,
        comment=payload.comment.strip(),
    )
    db.add(entry)
    db.commit()
    return _to_out(_load_entry(db, user, entry.id))


@router.patch("/{entry_id}", response_model=schemas.UserBookOut)
def update_entry(
    entry_id: int,
    payload: schemas.UserBookUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    entry = _load_entry(db, user, entry_id)
    if payload.status is None and payload.comment is None:
        raise HTTPException(
            400, detail={"code": "validation_error", "message": "Передайте status и/или comment."}
        )
    if payload.status is not None:
        entry.status = payload.status
    if payload.comment is not None:
        entry.comment = payload.comment.strip()
    db.commit()
    return _to_out(_load_entry(db, user, entry_id))


@router.delete("/{entry_id}")
def remove_from_library(
    entry_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    entry = _load_entry(db, user, entry_id)
    db.delete(entry)
    db.commit()
    return {"detail": "Книга удалена из библиотеки."}
