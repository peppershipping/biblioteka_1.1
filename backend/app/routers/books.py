
"""Book catalog, search, filtering, caching and book details."""

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
from ..schemas import (
    BookCreate,
    BookDetail,
    BookOut,
    BookPage,
    CatalogSort,
    GenreOut,
    SortOrder,
)
from ..services import books as books_service
from ..services import llm

router = APIRouter(
    prefix="/books",
    tags=["Книги"],
    dependencies=[DefaultLimit],
)
genres_router = APIRouter(
    tags=["Книги"],
    dependencies=[DefaultLimit],
)


def catalog_params(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: CatalogSort | None = Query(None),
    order: SortOrder = Query("asc"),
    q: str | None = Query(None, max_length=200),
    genre: str | None = Query(None, max_length=100),
    author: str | None = Query(None, max_length=200),
    year: int | None = Query(None, ge=1, le=2100),
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


def _catalog_page(
    db: Session,
    user: models.User | None,
    params: dict,
    smart: bool = False,
) -> dict:
    params = dict(params)
    interpreted = None

    if smart and params["q"] and get_settings().llm_enabled:
        genres = list(
            db.scalars(
                select(models.Genre.name).order_by(models.Genre.name)
            )
        )
        interpreted = llm.interpret_query(params["q"], genres)

        if interpreted:
            params["q"] = interpreted.get("q") or params["q"]
            params["genre"] = (
                params["genre"] or interpreted.get("genre")
            )
            params["year"] = (
                params["year"] or interpreted.get("year")
            )

    key_source = json.dumps(
        params,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    digest = hashlib.sha1(key_source.encode("utf-8")).hexdigest()
    key = f"catalog:v{cache.version('catalog')}:{digest}"

    cached = cache.get_json(key)

    if cached is None:
        found_books, total = books_service.search_books(
            db,
            **params,
        )
        cached = {
            "items": [
                BookOut.model_validate(book).model_dump(mode="json")
                for book in found_books
            ],
            "total": total,
        }
        cache.set_json(
            key,
            cached,
            get_settings().cache_catalog_ttl,
        )

    book_ids = [item["id"] for item in cached["items"]]
    overlay = books_service.user_overlay(
        db,
        user.id if user else None,
        book_ids,
    )

    items = []
    for item in cached["items"]:
        status, rating = overlay.get(item["id"], (None, None))
        items.append(
            {
                **item,
                "my_status": status,
                "my_rating": rating,
            }
        )

    return {
        "items": items,
        "limit": params["limit"],
        "offset": params["offset"],
        "total": cached["total"],
        "interpreted": interpreted,
    }


@router.get(
    "",
    response_model=BookPage,
    summary="Список книг",
)
def list_books(
    params: dict = Depends(catalog_params),
    user: models.User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return _catalog_page(db, user, params)


# Keep /search before /{book_id}, so "search" is not treated as an ID.
@router.get(
    "/search",
    response_model=BookPage,
    summary="Поиск книг",
)
def search_books(
    smart: bool = Query(False),
    params: dict = Depends(catalog_params),
    user: models.User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return _catalog_page(db, user, params, smart=smart)


@router.get(
    "/{book_id}",
    response_model=BookDetail,
    summary="Информация о книге",
)
def get_book(
    book_id: int = Path(ge=1),
    user: models.User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    book = db.scalar(
        select(models.Book)
        .where(models.Book.id == book_id)
        .options(
            selectinload(models.Book.authors),
            selectinload(models.Book.genres),
        )
    )

    if book is None:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    detail = BookDetail.model_validate(book)

    if user:
        entry = db.scalar(
            select(models.UserBook).where(
                models.UserBook.user_id == user.id,
                models.UserBook.book_id == book_id,
            )
        )

        if entry:
            detail.library_id = entry.id
            detail.my_status = entry.status
            overlay = books_service.user_overlay(
                db,
                user.id,
                [book_id],
            )
            detail.my_rating = overlay.get(book_id, (None, None))[1]

    detail.avg_rating, detail.ratings_count = (
        books_service.rating_summary(db, book_id)
    )

    return detail


@router.post(
    "",
    response_model=BookOut,
    status_code=201,
    summary="Добавить книгу в каталог (только admin)",
)
def create_book(
    payload: BookCreate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        book = books_service.create_book(
            db,
            **payload.model_dump(),
        )
        db.commit()
    except books_service.DuplicateBookError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Книга с таким названием и авторами уже есть в каталоге",
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Конфликт данных при добавлении книги",
        )

    cache.bump("catalog")
    db.refresh(book, attribute_names=["authors", "genres"])
    return BookOut.model_validate(book)


@genres_router.get(
    "/genres",
    response_model=list[GenreOut],
    summary="Список жанров",
)
def list_genres(db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Genre).order_by(models.Genre.name)
    ).all()
