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
