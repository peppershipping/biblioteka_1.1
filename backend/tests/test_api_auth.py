"""Регистрация, вход, токены (ТЗ 13.1 п.1–6, 13.3 «Регистрация», «Вход», 15.2)."""

import pytest
from sqlalchemy import text

from .conftest import PASSWORD, bearer, login, register

pytestmark = pytest.mark.db


def test_register_creates_user_without_exposing_secrets(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "anna" and body["role"] == "user"
    assert "password" not in body and "password_hash" not in body


def test_password_is_stored_as_argon2id_hash(client, db_session):
    register(client)
    stored = db_session.execute(text("SELECT password_hash FROM users WHERE username='anna'")).scalar()
    assert stored.startswith("$argon2id$") and PASSWORD not in stored


def test_duplicate_username_and_email_give_409(client):
    assert register(client).status_code == 201
    assert register(client, email="other@example.com").status_code == 409   # тот же username
    assert register(client, name="other").status_code == 201
    assert register(client, name="third", email="other@example.com").status_code == 409  # тот же email


def test_invalid_registration_data_gives_422_with_readable_errors(client):
    r = client.post("/api/v1/auth/register", json={"username": "a", "email": "not-an-email", "password": "123"})
    assert r.status_code == 422
    body = r.json()
    assert isinstance(body["detail"], str) and body["detail"].startswith("Ошибка валидации")
    fields = {e["field"] for e in body["errors"]}
    assert {"username", "email", "password"} <= fields
    assert "Traceback" not in r.text


def test_client_cannot_choose_own_role(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "mallory", "email": "m@example.com", "password": PASSWORD, "role": "admin"},
    )
    assert r.status_code == 201 and r.json()["role"] == "user"


def test_login_success_and_failures(client):
    register(client)
    ok = login(client)
    assert ok.status_code == 200
    tokens = ok.json()
    assert tokens["token_type"] == "bearer" and tokens["expires_in"] == 15 * 60
    assert tokens["access_token"] and tokens["refresh_token"]

    wrong = login(client, password="wrong-password")
    unknown = login(client, name="nobody")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # ответ не выдаёт, существует ли пользователь


def test_login_by_email_is_supported(client):
    register(client)
    r = client.post("/api/v1/auth/login", json={"username": "anna@example.com", "password": PASSWORD})
    assert r.status_code == 200


def test_me_requires_valid_token(client):
    register(client)
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    me = client.get("/api/v1/auth/me", headers=bearer(login(client).json()))
    assert me.status_code == 200 and me.json()["username"] == "anna"


def test_refresh_rotates_tokens_and_detects_reuse(client):
    register(client)
    first = login(client).json()
    second = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert second.status_code == 200
    new_tokens = second.json()
    assert new_tokens["refresh_token"] != first["refresh_token"]

    # старый токен отозван; его повторное предъявление отзывает и новый (подозрение на кражу)
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reuse.status_code == 401
    after_theft = client.post("/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert after_theft.status_code == 401


def test_logout_revokes_refresh_token(client):
    register(client)
    tokens = login(client).json()
    out = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    # неизвестный токен тоже даёт 204 — нельзя выяснить, существовал ли он
    assert client.post("/api/v1/auth/logout", json={"refresh_token": "x" * 40}).status_code == 204


def test_refresh_tokens_are_stored_hashed(client, db_session):
    register(client)
    raw = login(client).json()["refresh_token"]
    hashes = db_session.execute(text("SELECT token_hash FROM refresh_tokens")).scalars().all()
    assert hashes and raw not in hashes and all(len(h) == 64 for h in hashes)


def test_unversioned_alias_works(client):
    assert register(client).status_code == 201
    assert client.post("/api/auth/login", json={"username": "anna", "password": PASSWORD}).status_code == 200
