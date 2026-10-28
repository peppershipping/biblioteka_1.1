"""Рекомендации (ТЗ 8, 9, 15.1 правила 34–37, 17)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..ratelimit import DefaultLimit
from ..schemas import FeedbackIn, FeedbackOut, RecommendationsPage
from ..services import recommender

router = APIRouter(prefix="/recommendations", tags=["Рекомендации"], dependencies=[DefaultLimit])


@router.get(
    "",
    response_model=RecommendationsPage,
    summary="Мои рекомендации (персональные — от трёх оценок, иначе — популярное)",
)
def get_recommendations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return recommender.build_page(db, user, limit, offset)


@router.post("/feedback", response_model=FeedbackOut, summary="Обратная связь: полезно / не полезно")
def send_feedback(
    payload: FeedbackIn,
    response: Response,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """201 — ответ сохранён впервые, 200 — предыдущий ответ обновлён. Чужая рекомендация — 404."""
    rec = db.scalar(
        select(models.Recommendation).where(
            models.Recommendation.id == payload.recommendation_id, models.Recommendation.user_id == user.id
        )
    )
    if rec is None:
        raise HTTPException(404, "Рекомендация не найдена")
    response.status_code = 201 if rec.feedback is None else 200
    rec.feedback = payload.feedback
    db.commit()
    recommender.invalidate(user.id)  # «не полезно» исключает книгу из будущих подборок
    return FeedbackOut(recommendation_id=rec.id, feedback=payload.feedback)
