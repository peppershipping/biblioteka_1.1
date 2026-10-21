"""Общая база книг («будущий каталог»): поиск по названию/автору/описанию, карточка книги, добавление."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api", tags=["books"])


def _book_options():
    return (selectinload(models.Book.authors), selectinload(models.Book.genres))


@router.get("/books", response_model=list[schemas.BookOut])
def list_books(
    q: str | None = Query(None, description="Поиск по названию, автору, описанию"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    stmt = select(models.Book).options(*_book_options())

    if q and q.strip():
        term = q.strip()
        tsvector = func.to_tsvector(
            "russian",
            func.coalesce(models.Book.title, "")
            + " "
            + func.coalesce(models.Book.description, "")
            + " "
            + func.coalesce(models.Book.keywords, ""),
        )
        stmt = stmt.where(
            or_(
                tsvector.op("@@")(func.plainto_tsquery("russian", term)),
                models.Book.title.ilike(f"%{term}%"),
                models.Book.authors.any(models.Author.name.ilike(f"%{term}%")),
            )
        )

    stmt = stmt.order_by(models.Book.title).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.get("/books/{book_id}", response_model=schemas.BookWithLibraryOut)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    book = db.scalar(select(models.Book).options(*_book_options()).where(models.Book.id == book_id))
    if book is None:
        raise HTTPException(404, detail={"code": "not_found", "message": "Книга не найдена."})

    entry = db.scalar(
        select(models.UserBook)
        .options(selectinload(models.UserBook.rating))
        .where(models.UserBook.user_id == user.id, models.UserBook.book_id == book_id)
    )
    out = schemas.BookWithLibraryOut.model_validate(book)
    if entry:
        out.status = entry.status
        out.my_rating = entry.rating.total if entry.rating else None
    return out


@router.post("/books", response_model=schemas.BookOut, status_code=201)
def create_book(
    payload: schemas.BookCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    book = models.Book(
        title=payload.title.strip(),
        description=payload.description,
        keywords=payload.keywords,
        publication_year=payload.publication_year,
        cover_url=payload.cover_url,
    )
    book.authors = [get_or_create(db, models.Author, n) for n in payload.authors if n.strip()]
    book.genres = [get_or_create(db, models.Genre, n) for n in payload.genres if n.strip()]
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def get_or_create(db: Session, model, name: str):
    name = name.strip()
    obj = db.scalar(select(model).where(func.lower(model.name) == name.lower()))
    if obj is None:
        obj = model(name=name)
        db.add(obj)
        db.flush()
    return obj
