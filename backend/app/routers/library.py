
"""User library: books, reading status, ratings and statistics."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..ratelimit import DefaultLimit
from ..schemas import (
    LibraryCreate,
    LibraryItem,
    LibrarySort,
    LibraryStats,
    LibraryUpdate,
    Page,
    SortOrder,
)
from ..services import recommender

router = APIRouter(
    prefix="/library",
    tags=["Библиотека"],
    dependencies=[DefaultLimit],
)


@router.get("", response_model=Page[LibraryItem])
def list_library(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: LibrarySort = Query("added_at"),
    order: SortOrder = Query("desc"),
    status: models.ReadingStatus | None = Query(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    stmt = (
        select(models.UserBook)
        .where(models.UserBook.user_id == user.id)
        .options(
            selectinload(models.UserBook.book).selectinload(
                models.Book.authors
            ),
            selectinload(models.UserBook.book).selectinload(
                models.Book.genres
            ),
            selectinload(models.UserBook.rating),
        )
    )

    if status is not None:
        stmt = stmt.where(models.UserBook.status == status)

    sort_columns = {
        "added_at": models.UserBook.added_at,
        "title": models.Book.title,
        "status": models.UserBook.status,
    }

    stmt = stmt.join(models.UserBook.book)
    sort_column = sort_columns[sort]

    if order == "desc":
        stmt = stmt.order_by(sort_column.desc(), models.UserBook.id.desc())
    else:
        stmt = stmt.order_by(sort_column.asc(), models.UserBook.id.asc())

    count_stmt = select(func.count()).select_from(models.UserBook).where(
        models.UserBook.user_id == user.id
    )
    if status is not None:
        count_stmt = count_stmt.where(models.UserBook.status == status)

    total = db.scalar(count_stmt) or 0
    entries = db.scalars(stmt.limit(limit).offset(offset)).all()

    items = [
        LibraryItem(
            id=entry.id,
            book=entry.book,
            status=entry.status,
            added_at=entry.added_at,
            rating=entry.rating,
        )
        for entry in entries
    ]

    return Page[LibraryItem](
        items=items,
        limit=limit,
        offset=offset,
        total=total,
    )


@router.post("", response_model=LibraryItem, status_code=201)
def add_to_library(
    payload: LibraryCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    book = db.get(models.Book, payload.book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    existing = db.scalar(
        select(models.UserBook).where(
            models.UserBook.user_id == user.id,
            models.UserBook.book_id == payload.book_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Книга уже есть в вашей библиотеке",
        )

    entry = models.UserBook(
        user_id=user.id,
        book_id=payload.book_id,
        status=payload.status,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    recommender.invalidate(user.id)

    entry = db.scalar(
        select(models.UserBook)
        .where(models.UserBook.id == entry.id)
        .options(
            selectinload(models.UserBook.book).selectinload(
                models.Book.authors
            ),
            selectinload(models.UserBook.book).selectinload(
                models.Book.genres
            ),
            selectinload(models.UserBook.rating),
        )
    )

    return LibraryItem(
        id=entry.id,
        book=entry.book,
        status=entry.status,
        added_at=entry.added_at,
        rating=entry.rating,
    )


@router.patch("/{entry_id}", response_model=LibraryItem)
def update_library_entry(
    entry_id: int,
    payload: LibraryUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    entry = db.scalar(
        select(models.UserBook)
        .where(
            models.UserBook.id == entry_id,
            models.UserBook.user_id == user.id,
        )
        .options(
            selectinload(models.UserBook.book).selectinload(
                models.Book.authors
            ),
            selectinload(models.UserBook.book).selectinload(
                models.Book.genres
            ),
            selectinload(models.UserBook.rating),
        )
    )

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Запись в библиотеке не найдена",
        )

    if payload.status is not None:
        entry.status = payload.status

    db.commit()
    db.refresh(entry)
    recommender.invalidate(user.id)

    return LibraryItem(
        id=entry.id,
        book=entry.book,
        status=entry.status,
        added_at=entry.added_at,
        rating=entry.rating,
    )


@router.delete("/{entry_id}", status_code=204)
def remove_from_library(
    entry_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    entry = db.scalar(
        select(models.UserBook).where(
            models.UserBook.id == entry_id,
            models.UserBook.user_id == user.id,
        )
    )

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Запись в библиотеке не найдена",
        )

    db.delete(entry)
    db.commit()
    recommender.invalidate(user.id)


@router.get("/stats", response_model=LibraryStats)
def library_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    counts = db.execute(
        select(
            models.UserBook.status,
            func.count(models.UserBook.id),
        )
        .where(models.UserBook.user_id == user.id)
        .group_by(models.UserBook.status)
    ).all()

    by_status = {status: count for status, count in counts}
    total = sum(by_status.values())

    return LibraryStats(
        total=total,
        want_to_read=by_status.get(models.ReadingStatus.want_to_read, 0),
        in_progress=by_status.get(models.ReadingStatus.in_progress, 0),
        read=by_status.get(models.ReadingStatus.read, 0),
    )
