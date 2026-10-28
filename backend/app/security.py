"""
Безопасность: хеширование паролей Argon2id (ТЗ 13.2/14.3), JWT access-токены,
opaque refresh-токены (хранятся только в виде SHA-256 хеша).
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jose import JWTError, jwt

from .config import get_settings

_hasher = PasswordHasher()  # Argon2id с безопасными параметрами по умолчанию
# Хеш-«пустышка»: проверяется при неизвестном логине, чтобы время ответа не
# выдавало, существует ли пользователь.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# ----------------------------- access JWT ---------------------------------


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    """Возвращает (токен, срок жизни в секундах)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != "access" or not str(payload.get("sub", "")).isdigit():
        return None
    return payload


# ---------------------------- refresh-токены -------------------------------


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    """(токен для клиента, его хеш для БД). Токен случайный и высокоэнтропийный,
    поэтому быстрого SHA-256 достаточно."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def refresh_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_expire_days)
