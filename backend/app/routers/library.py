<<<<<<< HEAD
"""
Личная библиотека (ТЗ 4.1, 8, 17): список со статусами, добавление, смена
статуса, удаление. user_id всегда берётся из проверенного токена — чужие
записи недоступны (проверка владельца на сервере, ТЗ 14.3).
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..models import Book, Rating, ReadingStatus, UserBook
from ..ratelimit import DefaultLimit
from ..schemas import LibraryCreate, LibraryItem, LibrarySort, LibraryStats, LibraryUpdate, Page, SortOrder
from ..services import recommender

router = APIRouter(prefix="/library", tags=["Личная библиотека"], dependencies=[DefaultLimit])

_ENTRY_OPTIONS = (
    selectinload(UserBook.book).selectinload(Book.authors),
    selectinload(UserBook.book).selectinload(Book.genres),
    selectinload(UserBook.rating),
)


def _load_entry(db: Session, user_id: int, entry_id: int) -> UserBook:
    """Запись пользователя по id. Чужая и несуществующая запись неотличимы (404)."""
    entry = db.scalar(
        select(UserBook).where(UserBook.id == entry_id, UserBook.user_id == user_id).options(*_ENTRY_OPTIONS)
    )
    if entry is None:
        raise HTTPException(404, "Запись не найдена в вашей библиотеке")
    return entry


@router.get("", response_model=Page[LibraryItem], summary="Моя библиотека (фильтр по статусу, сортировка, пагинация)")
def list_library(
    status: ReadingStatus | None = Query(None, description="Фильтр по статусу чтения"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: LibrarySort = Query("added"),
    order: SortOrder = Query("desc"),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filters = [UserBook.user_id == user.id]
    if status is not None:
        filters.append(UserBook.status == status)

    total = db.scalar(select(func.count(UserBook.id)).where(*filters)) or 0

    columns = {
        "added": UserBook.added_at,
        "title": func.lower(Book.title),
        "status": UserBook.status,
        "rating": Rating.total,
    }
    column = columns[sort]
    direction = column.desc() if order == "desc" else column.asc()
    if sort == "rating":
        direction = direction.nulls_last()

    entries = db.scalars(
        select(UserBook)
        .join(Book, Book.id == UserBook.book_id)
        .outerjoin(Rating, Rating.user_book_id == UserBook.id)
        .where(*filters)
        .options(*_ENTRY_OPTIONS)
        .order_by(direction, UserBook.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": entries, "limit": limit, "offset": offset, "total": total}


@router.get("/stats", response_model=LibraryStats, summary="Статистика библиотеки (для профиля)")
def library_stats(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    counts = {
        status: count
        for status, count in db.execute(
            select(UserBook.status, func.count(UserBook.id)).where(UserBook.user_id == user.id).group_by(UserBook.status)
        ).all()
    }
    ratings_count, avg = db.execute(
        select(func.count(Rating.id), func.avg(Rating.total))
        .join(UserBook, UserBook.id == Rating.user_book_id)
        .where(UserBook.user_id == user.id)
    ).one()
    return LibraryStats(
        total=sum(counts.values()),
        want_to_read=counts.get(ReadingStatus.want_to_read, 0),
        in_progress=counts.get(ReadingStatus.in_progress, 0),
        read=counts.get(ReadingStatus.read, 0),
        ratings_count=int(ratings_count),
        avg_rating=round(float(avg), 1) if avg is not None else None,
    )


@router.post("", response_model=LibraryItem, status_code=201, summary="Добавить книгу в библиотеку")
def add_to_library(payload: LibraryCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(Book, payload.book_id) is None:
        raise HTTPException(404, "Книга не найдена в каталоге")
    duplicate = HTTPException(409, "Эта книга уже есть в вашей библиотеке")
    if db.scalar(select(UserBook.id).where(UserBook.user_id == user.id, UserBook.book_id == payload.book_id)):
        raise duplicate
    entry = UserBook(user_id=user.id, book_id=payload.book_id, status=payload.status)
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:  # одновременное добавление: сработал UNIQUE (user_id, book_id)
        db.rollback()
        raise duplicate
    recommender.invalidate(user.id)
    return _load_entry(db, user.id, entry.id)


@router.patch("/{entry_id}", response_model=LibraryItem, summary="Изменить статус чтения")
def update_status(
    payload: LibraryUpdate,
    entry_id: int = Path(ge=1),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _load_entry(db, user.id, entry_id)
    entry.status = payload.status
    db.commit()
    recommender.invalidate(user.id)
    return entry


@router.delete("/{entry_id}", status_code=204, summary="Удалить книгу из библиотеки (из каталога не удаляется)")
def delete_entry(entry_id: int = Path(ge=1), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = _load_entry(db, user.id, entry_id)
    db.delete(entry)  # оценка удаляется каскадно, книга каталога остаётся
    db.commit()
    recommender.invalidate(user.id)
    return Response(status_code=204)
=======
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
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
