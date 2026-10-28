"""
Фикстуры тестов. Интеграционные тесты (маркер db) работают на реальном
PostgreSQL — ENUM, триггеры и полнотекстовый поиск нельзя проверить на SQLite.
Укажите отдельную тестовую БД:

    TEST_DATABASE_URL=postgresql+psycopg://biblioteka:biblioteka@db:5432/biblioteka_test pytest

Схема создаётся миграциями Alembic — так заодно проверяется сама миграция.
"""

import os
from pathlib import Path

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")

# Настройки задаём ДО импорта приложения (get_settings кэшируется)
if TEST_DB:
    os.environ["DATABASE_URL"] = TEST_DB
os.environ["RATE_LIMIT_ENABLED"] = "false"   # включается точечно в тесте лимитов
os.environ["REDIS_URL"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["ADMIN_USERNAME"] = ""
os.environ["ADMIN_EMAIL"] = ""
os.environ["ADMIN_PASSWORD"] = ""

BACKEND_DIR = Path(__file__).resolve().parent.parent


def pytest_collection_modifyitems(config, items):
    if TEST_DB:
        return
    skip = pytest.mark.skip(reason="не задан TEST_DATABASE_URL — интеграционные тесты пропущены")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def migrated_db():
    """Пересоздаёт схему тестовой БД миграциями Alembic."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture()
def db_session(migrated_db):
    from sqlalchemy import text

    from app.database import SessionLocal, engine

    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE users, books, authors, genres, rating_audit RESTART IDENTITY CASCADE")
        )
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def client(db_session):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


# ----------------------------- помощники -----------------------------------

PASSWORD = "Secret123!"


def register(client, name="anna", email=None, password=PASSWORD):
    return client.post(
        "/api/v1/auth/register",
        json={"username": name, "email": email or f"{name}@example.com", "password": password},
    )


def login(client, name="anna", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": name, "password": password})


def bearer(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture()
def make_user(client):
    """Регистрирует пользователя и возвращает заголовок Authorization."""

    def _make(name="anna"):
        assert register(client, name).status_code == 201
        return bearer(login(client, name).json())

    return _make


@pytest.fixture()
def user_headers(make_user):
    return make_user("anna")


@pytest.fixture()
def admin_headers(client, db_session):
    from app import models
    from app.security import hash_password

    db_session.add(
        models.User(username="root", email="root@example.com", password_hash=hash_password(PASSWORD), role="admin")
    )
    db_session.commit()
    return bearer(login(client, "root").json())


@pytest.fixture()
def make_book(client, admin_headers):
    counter = {"n": 0}

    def _make(title=None, authors=("Автор",), genres=("Фэнтези",), year=2020, description="Описание книги"):
        counter["n"] += 1
        response = client.post(
            "/api/v1/books",
            headers=admin_headers,
            json={
                "title": title or f"Книга {counter['n']}",
                "authors": list(authors),
                "genres": list(genres),
                "publication_year": year,
                "description": description,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture()
def add_read_book(client):
    """Добавляет книгу в библиотеку со статусом «Прочитано» и ставит оценку."""

    def _add(headers, book_id, plot=8, characters=8, style=8):
        entry = client.post("/api/v1/library", headers=headers, json={"book_id": book_id, "status": "read"})
        assert entry.status_code == 201, entry.text
        rating = client.post(
            f"/api/v1/books/{book_id}/rating",
            headers=headers,
            json={"plot": plot, "characters": characters, "style": style},
        )
        assert rating.status_code == 201, rating.text
        return entry.json()

    return _add
