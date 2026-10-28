"""Личная библиотека и оценки (ТЗ 13.1 п.10–18, 15.1 правила 26–32, 38, 13.3)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db


# ------------------------------ библиотека ---------------------------------


def test_library_requires_authentication(client):
    assert client.get("/api/v1/library").status_code == 401
    assert client.post("/api/v1/library", json={"book_id": 1}).status_code == 401


def test_add_book_to_library_and_reject_duplicates(client, user_headers, make_book):
    book = make_book()
    r = client.post("/api/v1/library", headers=user_headers, json={"book_id": book["id"]})
    assert r.status_code == 201
    assert r.json()["status"] == "want_to_read" and r.json()["book"]["title"] == book["title"]
    assert client.post("/api/v1/library", headers=user_headers, json={"book_id": book["id"]}).status_code == 409
    assert client.post("/api/v1/library", headers=user_headers, json={"book_id": 999999}).status_code == 404
    assert client.post("/api/v1/library", headers=user_headers, json={"book_id": book["id"], "status": "x"}).status_code == 422


def test_status_can_be_changed_and_validated(client, user_headers, make_book):
    entry = client.post("/api/v1/library", headers=user_headers, json={"book_id": make_book()["id"]}).json()
    for status in ("in_progress", "read", "want_to_read"):
        r = client.patch(f"/api/v1/library/{entry['id']}", headers=user_headers, json={"status": status})
        assert r.status_code == 200 and r.json()["status"] == status
    assert client.patch(f"/api/v1/library/{entry['id']}", headers=user_headers, json={"status": "done"}).status_code == 422


def test_other_users_entries_are_not_accessible(client, user_headers, make_user, make_book):
    entry = client.post("/api/v1/library", headers=user_headers, json={"book_id": make_book()["id"]}).json()
    other = make_user("boris")
    assert client.patch(f"/api/v1/library/{entry['id']}", headers=other, json={"status": "read"}).status_code == 404
    assert client.delete(f"/api/v1/library/{entry['id']}", headers=other).status_code == 404
    assert client.get("/api/v1/library", headers=other).json()["total"] == 0


def test_delete_removes_only_the_personal_entry(client, user_headers, make_book):
    book = make_book()
    entry = client.post("/api/v1/library", headers=user_headers, json={"book_id": book["id"]}).json()
    assert client.delete(f"/api/v1/library/{entry['id']}", headers=user_headers).status_code == 204
    assert client.get("/api/v1/library", headers=user_headers).json()["total"] == 0
    assert client.get(f"/api/v1/books/{book['id']}").status_code == 200  # из каталога не удалена


def test_library_filter_sort_pagination_and_stats(client, user_headers, make_book, add_read_book):
    a, b, c = make_book(title="А"), make_book(title="Б"), make_book(title="В")
    add_read_book(user_headers, a["id"], 10, 10, 10)
    client.post("/api/v1/library", headers=user_headers, json={"book_id": b["id"], "status": "in_progress"})
    client.post("/api/v1/library", headers=user_headers, json={"book_id": c["id"]})

    only_read = client.get("/api/v1/library", headers=user_headers, params={"status": "read"}).json()
    assert only_read["total"] == 1 and only_read["items"][0]["book"]["title"] == "А"
    assert only_read["items"][0]["rating"]["total"] == 10.0

    page = client.get("/api/v1/library", headers=user_headers, params={"sort": "title", "order": "asc", "limit": 2}).json()
    assert [i["book"]["title"] for i in page["items"]] == ["А", "Б"] and page["total"] == 3

    assert client.get("/api/v1/library", headers=user_headers, params={"sort": "price"}).status_code == 422

    stats = client.get("/api/v1/library/stats", headers=user_headers).json()
    assert stats == {"total": 3, "want_to_read": 1, "in_progress": 1, "read": 1, "ratings_count": 1, "avg_rating": 10.0}


# -------------------------------- оценки -----------------------------------


def _entry(client, headers, book_id, status):
    return client.post("/api/v1/library", headers=headers, json={"book_id": book_id, "status": status}).json()


def test_rating_requires_book_in_library(client, user_headers, make_book):
    r = client.post(f"/api/v1/books/{make_book()['id']}/rating", headers=user_headers, json={"plot": 5, "characters": 5, "style": 5})
    assert r.status_code == 404


@pytest.mark.parametrize("status", ["want_to_read", "in_progress"])
def test_rating_is_forbidden_until_book_is_read(client, user_headers, make_book, status):
    book = make_book()
    _entry(client, user_headers, book["id"], status)
    r = client.post(f"/api/v1/books/{book['id']}/rating", headers=user_headers, json={"plot": 5, "characters": 5, "style": 5})
    assert r.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"plot": 0, "characters": 5, "style": 5},
        {"plot": 11, "characters": 5, "style": 5},
        {"plot": 5, "characters": 5},
        {"plot": 5.5, "characters": 5, "style": 5},
        {"plot": "5", "characters": 5, "style": 5},
        {"plot": True, "characters": 5, "style": 5},
    ],
)
def test_rating_values_must_be_integers_1_to_10(client, user_headers, make_book, payload):
    book = make_book()
    _entry(client, user_headers, book["id"], "read")
    assert client.post(f"/api/v1/books/{book['id']}/rating", headers=user_headers, json=payload).status_code == 422


def test_total_is_mean_of_three_criteria_rounded_to_one_decimal(client, user_headers, make_book):
    book = make_book()
    _entry(client, user_headers, book["id"], "read")
    url = f"/api/v1/books/{book['id']}/rating"

    created = client.post(url, headers=user_headers, json={"plot": 8, "characters": 9, "style": 7})
    assert created.status_code == 201 and created.json()["total"] == 8.0

    replaced = client.post(url, headers=user_headers, json={"plot": 9, "characters": 9, "style": 8})
    assert replaced.status_code == 200 and replaced.json()["total"] == 8.7

    patched = client.patch(url, headers=user_headers, json={"style": 10})
    assert patched.status_code == 200
    assert patched.json()["style"] == 10 and patched.json()["total"] == 9.3

    assert client.get(url, headers=user_headers).json()["total"] == 9.3
    assert client.patch(url, headers=user_headers, json={}).status_code == 422


def test_patch_without_existing_rating_gives_404(client, user_headers, make_book):
    book = make_book()
    _entry(client, user_headers, book["id"], "read")
    assert client.patch(f"/api/v1/books/{book['id']}/rating", headers=user_headers, json={"plot": 5}).status_code == 404
    assert client.get(f"/api/v1/books/{book['id']}/rating", headers=user_headers).status_code == 404


def test_total_is_computed_by_database_trigger_too(client, user_headers, make_book, add_read_book, db_session):
    add_read_book(user_headers, make_book()["id"], 8, 9, 7)
    # обновляем критерий «мимо» приложения: триггер БД должен пересчитать total сам
    db_session.execute(text("UPDATE ratings SET plot = 10"))
    db_session.commit()
    total = db_session.execute(text("SELECT total FROM ratings")).scalar()
    assert float(total) == 8.7  # (10 + 9 + 7) / 3


def test_rating_changes_are_audited_with_user_id(client, user_headers, make_book, add_read_book, db_session):
    book = make_book()
    add_read_book(user_headers, book["id"], 5, 5, 5)
    client.patch(f"/api/v1/books/{book['id']}/rating", headers=user_headers, json={"plot": 9})
    row = db_session.execute(text("SELECT old_plot, new_plot, changed_by FROM rating_audit")).one()
    user_id = db_session.execute(text("SELECT id FROM users WHERE username = 'anna'")).scalar()
    assert (row.old_plot, row.new_plot, row.changed_by) == (5, 9, user_id)


def test_deleting_library_entry_removes_rating_but_keeps_book(client, user_headers, make_book, add_read_book, db_session):
    book = make_book()
    entry = add_read_book(user_headers, book["id"])
    client.delete(f"/api/v1/library/{entry['id']}", headers=user_headers)
    assert db_session.execute(text("SELECT count(*) FROM ratings")).scalar() == 0
    assert client.get(f"/api/v1/books/{book['id']}").status_code == 200


def test_all_ratings_of_book_expose_username_not_email(client, user_headers, make_user, make_book, add_read_book):
    book = make_book()
    add_read_book(user_headers, book["id"], 8, 8, 8)
    add_read_book(make_user("boris"), book["id"], 6, 6, 6)
    r = client.get(f"/api/v1/books/{book['id']}/ratings")
    assert r.status_code == 200 and r.json()["total"] == 2
    assert {i["username"] for i in r.json()["items"]} == {"anna", "boris"}
    assert "email" not in r.text
    assert client.get("/api/v1/books/999999/ratings").status_code == 404

    detail = client.get(f"/api/v1/books/{book['id']}").json()
    assert detail["avg_rating"] == 7.0 and detail["ratings_count"] == 2


def test_my_rating_endpoint_returns_only_my_rating(client, user_headers, make_user, make_book, add_read_book):
    book = make_book()
    add_read_book(user_headers, book["id"], 9, 9, 9)
    other = make_user("boris")
    client.post("/api/v1/library", headers=other, json={"book_id": book["id"], "status": "read"})
    # у Бориса оценки нет — чужую он не увидит
    assert client.get(f"/api/v1/books/{book['id']}/rating", headers=other).status_code == 404
