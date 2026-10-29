"""Password hashing and access/refresh token utilities."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jose import JWTError, jwt

from .config import get_settings

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        valid = _hasher.verify(password_hash or _DUMMY_HASH, password)
        return bool(valid and password_hash is not None)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
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

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None

    if payload.get("type") != "access":
        return None

    if not str(payload.get("sub", "")).isdigit():
        return None

    return payload


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    """Return a raw refresh token and its SHA-256 hash."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def refresh_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=get_settings().refresh_token_expire_days
    )
