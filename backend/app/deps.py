from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False,
)


def _user_from_token(
    token: str | None,
    db: Session,
) -> models.User | None:
    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None

    return db.get(models.User, user_id)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    user = _user_from_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User | None:
    """Return the current user when a valid token is provided."""
    return _user_from_token(token, db)


def require_admin(
    user: models.User = Depends(get_current_user),
) -> models.User:
    if user.role != models.ROLE_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Administrator privileges required",
        )
    return user