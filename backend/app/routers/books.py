<<<<<<< HEAD
"""
Каталог книг (ТЗ 4.3, 8, 17): список с пагинацией, поиск и фильтры, карточка
книги, добавление в общий каталог (только admin).

Каталог доступен гостям; если передан токен, в карточки добавляются статус и
оценка текущего пользователя. Страница «чистых» данных книг кэшируется в Redis
на 5 минут (ТЗ 15.4), персональные поля подмешиваются после чтения из кэша.
"""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .. import cache, models
from ..config import get_settings
from ..database import get_db
from ..deps import get_optional_user, require_admin
from ..ratelimit import DefaultLimit
from ..schemas import BookCreate, BookDetail, BookOut, BookPage, CatalogSort, GenreOut, SortOrder
from ..services import books as books_service
from ..services import llm

router = APIRouter(prefix="/books", tags=["Книги"], dependencies=[DefaultLimit])
genres_router = APIRouter(tags=["Книги"], dependencies=[DefaultLimit])


def catalog_params(
    limit: int = Query(20, ge=1, le=100, description="Размер страницы (по умолчанию 20, максимум 100)"),
    offset: int = Query(0, ge=0, description="Смещение"),
    sort: CatalogSort | None = Query(None, description="Сортировка (по умолчанию: релевантность при поиске, иначе название)"),
    order: SortOrder = Query("asc"),
    q: str | None = Query(None, max_length=200, description="Поиск по названию, описанию, автору, жанру"),
    genre: str | None = Query(None, max_length=100, description="Точное название жанра"),
    author: str | None = Query(None, max_length=200, description="Часть имени автора"),
    year: int | None = Query(None, ge=1, le=2100, description="Год публикации"),
) -> dict:
    return {
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "order": order,
        "q": (q or "").strip() or None,
        "genre": (genre or "").strip() or None,
        "author": (author or "").strip() or None,
        "year": year,
    }


def _catalog_page(db: Session, user: models.User | None, params: dict, smart: bool = False) -> dict:
    params = dict(params)
    interpreted = None
    if smart and params["q"] and get_settings().llm_enabled:
        genres = list(db.scalars(select(models.Genre.name).order_by(models.Genre.name)))
        interpreted = llm.interpret_query(params["q"], genres)
        if interpreted:  # явно заданные пользователем фильтры важнее разобранных моделью
            params["q"] = interpreted["q"]
            params["genre"] = params["genre"] or interpreted["genre"]
            params["year"] = params["year"] or interpreted["year"]

    key_src = json.dumps(params, sort_keys=True, ensure_ascii=False)
    key = f"catalog:v{cache.version('catalog')}:{hashlib.sha1(key_src.encode()).hexdigest()}"
    cached = cache.get_json(key)
    if cached is None:
        books, total = books_service.search_books(db, **params)
        cached = {"items": [BookOut.model_validate(b).model_dump() for b in books], "total": total}
        cache.set_json(key, cached, get_settings().cache_catalog_ttl)

    overlay = books_service.user_overlay(db, user.id if user else None, [it["id"] for it in cached["items"]])
    items = []
    for it in cached["items"]:
        status, rating = overlay.get(it["id"], (None, None))
        items.append({**it, "my_status": status, "my_rating": rating})
    return {
        "items": items,
        "limit": params["limit"],
        "offset": params["offset"],
        "total": cached["total"],
        "interpreted": interpreted,
    }


@router.get("", response_model=BookPage, summary="Список книг (пагинация, фильтры, сортировка)")
def list_books(
    params: dict = Depends(catalog_params),
    user: models.User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return _catalog_page(db, user, params)


# ВАЖНО: /search объявлен раньше /{book_id}, иначе «search» разбирался бы как id
@router.get("/search", response_model=BookPage, summary="Поиск книг (PostgreSQL Full-Text Search)")
def search_books(
    smart: bool = Query(False, description="Умный поиск: языковая модель разбирает запрос на естественном языке"),
    params: dict = Depends(catalog_params),
    user: models.User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return _catalog_page(db, user, params, smart=smart)


@router.get("/{book_id}", response_model=BookDetail, summary="Информация о книге")
def get_book(
    book_id: int = Path(ge=1),
    user: models.User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    book = db.scalar(
        select(models.Book)
        .where(models.Book.id == book_id)
        .options(selectinload(models.Book.authors), selectinload(models.Book.genres))
    )
    if book is None:
        raise HTTPException(404, "Книга не найдена")
    detail = BookDetail.model_validate(book)
    if user:
        entry = db.scalar(
            select(models.UserBook).where(models.UserBook.user_id == user.id, models.UserBook.book_id == book_id)
        )
        if entry:
            detail.library_id = entry.id
            detail.my_status = entry.status
            overlay = books_service.user_overlay(db, user.id, [book_id])
            detail.my_rating = overlay.get(book_id, (None, None))[1]
    detail.avg_rating, detail.ratings_count = books_service.rating_summary(db, book_id)
    return detail


@router.post("", response_model=BookOut, status_code=201, summary="Добавить книгу в общий каталог (только admin)")
def create_book(payload: BookCreate, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        book = books_service.create_book(db, **payload.model_dump())
        db.commit()
    except books_service.DuplicateBookError:
        db.rollback()
        raise HTTPException(409, "Книга с таким названием и авторами уже есть в каталоге")
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Конфликт данных при добавлении книги")
    cache.bump("catalog")
    db.refresh(book, attribute_names=["authors", "genres"])
    return BookOut.model_validate(book)


@genres_router.get("/genres", response_model=list[GenreOut], summary="Список жанров")
def list_genres(db: Session = Depends(get_db)):
    return db.scalars(select(models.Genre).order_by(models.Genre.name)).all()
=======
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
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
