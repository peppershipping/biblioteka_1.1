"""
Аутентификация (ТЗ 8, 15.2, 17): регистрация, вход, обновление и отзыв токенов.

Access JWT живёт 15 минут, refresh-токен — 7 дней. Refresh хранится только
как SHA-256 хеш; при каждом обновлении старый токен отзывается (ротация), а
повторное предъявление уже отозванного токена считается признаком кражи —
отзываются все токены пользователя.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..ratelimit import AuthLimit, DefaultLimit
from ..schemas import LoginIn, RefreshIn, TokenPair, UserCreate, UserOut
from ..security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    password_needs_rehash,
    refresh_expires_at,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Аутентификация"])

def _bad_credentials() -> HTTPException:
    return HTTPException(401, "Неверное имя пользователя или пароль", headers={"WWW-Authenticate": "Bearer"})


def _issue_tokens(db: Session, user: models.User) -> TokenPair:
    access, expires_in = create_access_token(user.id, user.role)
    raw, token_hash = new_refresh_token()
    db.add(models.RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=refresh_expires_at()))
    return TokenPair(access_token=access, refresh_token=raw, expires_in=expires_in)


def _authenticate(db: Session, login: str, password: str) -> models.User:
    login = login.strip()
    user = db.scalar(
        select(models.User).where(
            or_(func.lower(models.User.username) == login.lower(), models.User.email == login.lower())
        )
    )
    # verify_password выполняется и для несуществующего пользователя — одинаковое время ответа
    if not verify_password(password, user.password_hash if user else None) or user is None:
        raise _bad_credentials()
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


@router.post("/register", response_model=UserOut, status_code=201, dependencies=[AuthLimit])
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(models.User.id).where(func.lower(models.User.username) == payload.username.lower())):
        raise HTTPException(409, "Имя пользователя уже занято")
    if db.scalar(select(models.User.id).where(models.User.email == payload.email)):
        raise HTTPException(409, "Пользователь с таким email уже зарегистрирован")
    user = models.User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=models.ROLE_USER,  # роль задаёт только сервер
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # гонка двух одинаковых регистраций
        db.rollback()
        raise HTTPException(409, "Пользователь с таким именем или email уже существует")
    return user


@router.post("/login", response_model=TokenPair, dependencies=[AuthLimit])
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = _authenticate(db, payload.username, payload.password)
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


@router.post("/token", response_model=TokenPair, dependencies=[AuthLimit], summary="OAuth2 Password flow (форма)")
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Тот же вход, но в формате OAuth2 password flow — для кнопки Authorize в Swagger."""
    user = _authenticate(db, form.username, form.password)
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair, dependencies=[AuthLimit])
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    row = db.scalar(
        select(models.RefreshToken)
        .where(models.RefreshToken.token_hash == hash_refresh_token(payload.refresh_token))
        .with_for_update()
    )
    invalid = HTTPException(401, "Недействительный refresh-токен", headers={"WWW-Authenticate": "Bearer"})
    if row is None:
        raise invalid
    if row.revoked_at is not None:
        # Повторное использование отозванного токена: возможна кража — отзываем все токены пользователя
        db.execute(
            update(models.RefreshToken)
            .where(models.RefreshToken.user_id == row.user_id, models.RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise invalid
    if row.expires_at <= now:
        raise HTTPException(401, "Срок действия refresh-токена истёк", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(models.User, row.user_id)
    if user is None:
        raise invalid
    row.revoked_at = now  # ротация: старый токен больше не действует
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


@router.post("/logout", status_code=204, dependencies=[DefaultLimit])
def logout(payload: RefreshIn, db: Session = Depends(get_db)):
    """
    Отзывает refresh-токен. Access-токен не нужен: он короткоживущий и истекает
    сам, а выйти нужно уметь и после его истечения. Ответ всегда 204 — так нельзя
    выяснить, существовал ли токен.
    """
    db.execute(
        update(models.RefreshToken)
        .where(
            models.RefreshToken.token_hash == hash_refresh_token(payload.refresh_token),
            models.RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=UserOut, dependencies=[DefaultLimit])
def me(user: models.User = Depends(get_current_user)):
    return user
