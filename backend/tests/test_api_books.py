"""Каталог, поиск, права admin (ТЗ 13.1 п.7–9, 19, 13.3 «Поиск»)."""

import pytest

pytestmark = pytest.mark.db


def test_catalog_is_public_and_paginated(client, make_book):
    for i in range(3):
        make_book(title=f"Книга {i}")
    r = client.get("/api/v1/books", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["limit"] == 2 and body["offset"] == 0 and body["total"] == 3 and len(body["items"]) == 2
    assert client.get("/api/v1/books", params={"limit": 2, "offset": 2}).json()["items"][0]["title"] == "Книга 2"


@pytest.mark.parametrize("params", [{"limit": 101}, {"limit": 0}, {"offset": -1}, {"sort": "price"}, {"order": "up"}, {"year": 0}])
def test_invalid_pagination_and_sort_parameters_give_422(client, params):
    assert client.get("/api/v1/books", params=params).status_code == 422


def test_default_page_size_is_20(client):
    assert client.get("/api/v1/books").json()["limit"] == 20


def test_only_admin_can_create_books(client, user_headers, admin_headers):
    payload = {"title": "Новая книга", "authors": ["Автор"], "genres": ["Драма"], "publication_year": 2024}
    assert client.post("/api/v1/books", json=payload).status_code == 401
    assert client.post("/api/v1/books", json=payload, headers=user_headers).status_code == 403
    created = client.post("/api/v1/books", json=payload, headers=admin_headers)
    assert created.status_code == 201
    assert created.json()["authors"] == ["Автор"] and created.json()["genres"] == ["Драма"]


def test_duplicate_book_gives_409(client, admin_headers):
    payload = {"title": "Одна и та же", "authors": ["Автор"]}
    assert client.post("/api/v1/books", json=payload, headers=admin_headers).status_code == 201
    assert client.post("/api/v1/books", json=payload, headers=admin_headers).status_code == 409


def test_book_creation_validation(client, admin_headers):
    r = client.post("/api/v1/books", json={"title": "  ", "cover_url": "ftp://x"}, headers=admin_headers)
    assert r.status_code == 422


def test_book_detail_and_404(client, make_book):
    book = make_book(authors=("Лев Толстой",), genres=("Классика",), year=1869)
    r = client.get(f"/api/v1/books/{book['id']}")
    assert r.status_code == 200
    assert r.json()["authors"] == ["Лев Толстой"] and r.json()["publication_year"] == 1869
    assert client.get("/api/v1/books/999999").status_code == 404


def test_search_by_title_author_genre_year_and_description(client, make_book):
    make_book(title="Война и мир", authors=("Лев Толстой",), genres=("Классика",), year=1869, description="Эпопея о войне")
    make_book(title="Дюна", authors=("Фрэнк Герберт",), genres=("Научная фантастика",), year=1965, description="Пустынная планета")

    def titles(**params):
        return [b["title"] for b in client.get("/api/v1/books/search", params=params).json()["items"]]

    assert titles(q="Дюна") == ["Дюна"]
    assert titles(q="Толстой") == ["Война и мир"]
    assert titles(q="толст") == ["Война и мир"]              # неполное слово
    assert titles(q="пустынная планета") == ["Дюна"]          # описание, полнотекстовый поиск
    assert titles(q="классика") == ["Война и мир"]            # жанр входит в вектор поиска
    assert titles(genre="Научная фантастика") == ["Дюна"]
    assert titles(year=1869) == ["Война и мир"]
    assert titles(author="герберт") == ["Дюна"]
    assert titles(q="несуществующее слово") == []             # нет совпадений — пустой список, не ошибка


def test_search_is_safe_against_injection_strings(client, make_book):
    make_book()
    for evil in ["'; DROP TABLE books; --", "%", "_", "\\", '" OR 1=1 --']:
        assert client.get("/api/v1/books/search", params={"q": evil}).status_code == 200
    assert client.get("/api/v1/books").json()["total"] == 1


def test_catalog_sorting_whitelist(client, make_book):
    make_book(title="Б", year=2000)
    make_book(title="А", year=2010)
    by_title = [b["title"] for b in client.get("/api/v1/books", params={"sort": "title"}).json()["items"]]
    by_year_desc = [b["title"] for b in client.get("/api/v1/books", params={"sort": "year", "order": "desc"}).json()["items"]]
    assert by_title == ["А", "Б"] and by_year_desc == ["А", "Б"]


def test_catalog_cards_include_my_status_and_rating_for_authenticated_user(client, user_headers, make_book, add_read_book):
    book = make_book()
    add_read_book(user_headers, book["id"], 8, 9, 7)
    anonymous = client.get("/api/v1/books").json()["items"][0]
    mine = client.get("/api/v1/books", headers=user_headers).json()["items"][0]
    assert anonymous["my_status"] is None and anonymous["my_rating"] is None
    assert mine["my_status"] == "read" and mine["my_rating"] == 8.0


def test_genres_list(client, make_book):
    make_book(genres=("Фэнтези", "Приключения"))
    assert [g["name"] for g in client.get("/api/v1/genres").json()] == ["Приключения", "Фэнтези"]
