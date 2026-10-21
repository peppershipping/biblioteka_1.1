"""Регистрация, вход, выход, профиль (JWT, см. отчёт, раздел 5)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _err(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


@router.post("/register", response_model=schemas.TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    exists = db.scalar(
        select(models.User).where(func.lower(models.User.username) == payload.username.lower())
    )
    if exists:
        raise _err(400, "validation_error", "Пользователь с таким именем уже существует.")
    if payload.email:
        email_taken = db.scalar(
            select(models.User).where(func.lower(models.User.email) == payload.email.lower())
        )
        if email_taken:
            raise _err(400, "validation_error", "Этот email уже используется.")

    user = models.User(
        username=payload.username.strip(),
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.TokenOut(access_token=create_access_token(str(user.id)), user=user)


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(
        select(models.User).where(func.lower(models.User.username) == payload.username.strip().lower())
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise _err(401, "invalid_credentials", "Неверное имя пользователя или пароль.")
    return schemas.TokenOut(access_token=create_access_token(str(user.id)), user=user)


@router.post("/logout")
def logout(_: models.User = Depends(get_current_user)):
    # JWT без состояния: фактический выход — удаление токена на клиенте.
    return {"detail": "Вы вышли из системы."}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
