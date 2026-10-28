"""Служебные маршруты: проверка живости (для Docker healthcheck и мониторинга)."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter(tags=["Служебные"])


@router.get("/health", summary="Проверка работоспособности")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"detail": "База данных недоступна"}, status_code=503)
    return {"status": "ok"}
