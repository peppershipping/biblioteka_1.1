"""Начальные данные при запуске: администратор и (по желанию) демо-каталог."""

import logging

from sqlalchemy import func, or_, select

from .. import models
from ..config import get_settings
from ..database import SessionLocal
from ..security import hash_password
from . import books as books_service

logger = logging.getLogger(__name__)


def seed_admin(db) -> None:
    s = get_settings()
    if not (s.admin_username and s.admin_email and s.admin_password):
        return
    exists = db.scalar(
        select(models.User.id).where(
            or_(
                func.lower(models.User.username) == s.admin_username.lower(),
                func.lower(models.User.email) == s.admin_email.lower(),
            )
        )
    )
    if exists:
        return
    db.add(
        models.User(
            username=s.admin_username,
            email=s.admin_email.lower(),
            password_hash=hash_password(s.admin_password),
            role=models.ROLE_ADMIN,
        )
    )
    db.commit()
    logger.info("Создан администратор %s", s.admin_username)


def seed_demo_books(db) -> None:
    if not get_settings().seed_demo_data:
        return
    if db.scalar(select(func.count()).select_from(models.Book)):
        return
    from ..seed_data import BOOKS

    for title, authors, genres, year, description in BOOKS:
        books_service.create_book(
            db, title=title, authors=authors, genres=genres, publication_year=year, description=description
        )
    db.commit()
    logger.info("Загружен демо-каталог: %s книг", len(BOOKS))


def run() -> None:
    with SessionLocal() as db:
        seed_admin(db)
        seed_demo_books(db)
