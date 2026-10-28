"""Единый формат ошибок, служебные маршруты, rate limiting, request_id (ТЗ 13.2, 15.3, 17.1)."""

import pytest

from .conftest import PASSWORD, register

pytestmark = pytest.mark.db


def test_health_endpoints(client):
    for path in ("/health", "/api/health", "/api/v1/health"):
        r = client.get(path)
        assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_error_format_is_detail_string_without_internals(client):
    not_found = client.get("/api/v1/books/999999")
    unauthorized = client.get("/api/v1/library")
    unknown_route = client.get("/api/v1/no-such-route")
    for response, status in ((not_found, 404), (unauthorized, 401), (unknown_route, 404)):
        assert response.status_code == status
        body = response.json()
        assert isinstance(body["detail"], str) and body["detail"]
        assert "Traceback" not in response.text and "sqlalchemy" not in response.text.lower()


def test_every_response_has_request_id_and_security_headers(client):
    r = client.get("/health")
    assert len(r.headers["x-request-id"]) >= 8
    assert r.headers["x-content-type-options"] == "nosniff"
    custom = client.get("/health", headers={"X-Request-ID": "abc-12345678"})
    assert custom.headers["x-request-id"] == "abc-12345678"
    hostile = client.get("/health", headers={"X-Request-ID": "bad id with spaces"})
    assert hostile.headers["x-request-id"] != "bad id with spaces"


def test_api_responses_are_not_cached(client):
    assert client.get("/api/v1/books").headers["cache-control"] == "no-store"


def test_login_is_rate_limited(client, monkeypatch):
    from app.config import get_settings
    from app.ratelimit import reset_memory_limiter

    register(client)
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    monkeypatch.setattr(get_settings(), "rate_limit_auth", 3)
    reset_memory_limiter()
    codes = [
        client.post("/api/v1/auth/login", json={"username": "anna", "password": PASSWORD}).status_code for _ in range(5)
    ]
    assert codes[:3] == [200, 200, 200] and codes[3:] == [429, 429]
    limited = client.post("/api/v1/auth/login", json={"username": "anna", "password": PASSWORD})
    assert "retry-after" in limited.headers and isinstance(limited.json()["detail"], str)
    reset_memory_limiter()


def test_metrics_endpoint_exposes_request_counters(client):
    client.get("/api/v1/books")
    text = client.get("/metrics").text
    assert "http_requests_total" in text and "http_request_duration_seconds" in text


def test_docs_are_available_in_development(client):
    assert client.get("/openapi.json").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/books" in paths and "/api/books" not in paths  # алиас без версии в схему не попадает
