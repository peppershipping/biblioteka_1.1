"""Рекомендации и обратная связь (ТЗ 13.1 п.21–23, 15.1 правила 34–37, 13.3)."""

import pytest

pytestmark = pytest.mark.db

FANTASY = ("Фэнтези",)
SCIFI = ("Научная фантастика",)


@pytest.fixture()
def catalog(make_book):
    """Три фэнтези-книги для оценок + кандидаты разных жанров."""
    return {
        "liked": [
            make_book(title=f"Фэнтези {i}", authors=("Толкин",), genres=FANTASY, description="магия дракон путешествие")
            for i in range(3)
        ],
        "candidate": make_book(title="Новое фэнтези", authors=("Толкин",), genres=FANTASY, description="магия кольцо дракон"),
        "other": make_book(title="Космос", authors=("Азимов",), genres=SCIFI, description="империя звёзды будущее"),
    }


def test_recommendations_require_authentication(client):
    assert client.get("/api/v1/recommendations").status_code == 401


def test_fewer_than_three_ratings_gives_message_and_nonpersonal_list(client, user_headers, catalog, add_read_book):
    add_read_book(user_headers, catalog["liked"][0]["id"], 9, 9, 9)
    r = client.get("/api/v1/recommendations", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["personalized"] is False and body["ratings_count"] == 1 and body["min_ratings"] == 3
    assert "трёх оценок" in body["message"]
    shown = {i["book"]["id"] for i in body["items"]}
    assert catalog["liked"][0]["id"] not in shown          # книга из библиотеки не рекомендуется
    assert body["items"] and all(i["reason"] is None for i in body["items"])


def test_personalized_after_three_ratings_excludes_library_books(client, user_headers, catalog, add_read_book):
    for book in catalog["liked"]:
        add_read_book(user_headers, book["id"], 9, 9, 9)
    body = client.get("/api/v1/recommendations", headers=user_headers).json()
    assert body["personalized"] is True and body["ratings_count"] == 3 and body["message"] is None
    ids = [i["book"]["id"] for i in body["items"]]
    assert ids[0] == catalog["candidate"]["id"]             # похожая книга — первая
    assert not set(ids) & {b["id"] for b in catalog["liked"]}
    top = body["items"][0]
    assert top["score"] > 0 and top["signals"]["genres"] == ["Фэнтези"] and top["signals"]["similar_to"]
    assert top["reason"] is None                              # языковая модель не настроена — без пояснений


def test_recommendations_pagination_and_validation(client, user_headers, catalog, add_read_book):
    for book in catalog["liked"]:
        add_read_book(user_headers, book["id"])
    page = client.get("/api/v1/recommendations", headers=user_headers, params={"limit": 1, "offset": 0}).json()
    assert page["limit"] == 1 and len(page["items"]) == 1 and page["total"] >= 1
    assert client.get("/api/v1/recommendations", headers=user_headers, params={"limit": 500}).status_code == 422


def test_feedback_is_saved_updated_and_validated(client, user_headers, catalog, add_read_book):
    for book in catalog["liked"]:
        add_read_book(user_headers, book["id"])
    rec_id = client.get("/api/v1/recommendations", headers=user_headers).json()["items"][0]["id"]

    first = client.post("/api/v1/recommendations/feedback", headers=user_headers, json={"recommendation_id": rec_id, "feedback": "helpful"})
    assert first.status_code == 201 and first.json() == {"recommendation_id": rec_id, "feedback": "helpful"}
    again = client.post("/api/v1/recommendations/feedback", headers=user_headers, json={"recommendation_id": rec_id, "feedback": "not_helpful"})
    assert again.status_code == 200 and again.json()["feedback"] == "not_helpful"

    assert client.post("/api/v1/recommendations/feedback", headers=user_headers, json={"recommendation_id": rec_id, "feedback": "meh"}).status_code == 422
    assert client.post("/api/v1/recommendations/feedback", headers=user_headers, json={"recommendation_id": 999999, "feedback": "helpful"}).status_code == 404


def test_feedback_on_foreign_recommendation_is_rejected(client, user_headers, make_user, catalog, add_read_book):
    for book in catalog["liked"]:
        add_read_book(user_headers, book["id"])
    rec_id = client.get("/api/v1/recommendations", headers=user_headers).json()["items"][0]["id"]
    intruder = make_user("boris")
    r = client.post("/api/v1/recommendations/feedback", headers=intruder, json={"recommendation_id": rec_id, "feedback": "helpful"})
    assert r.status_code == 404


def test_not_helpful_book_is_not_recommended_again(client, user_headers, catalog, add_read_book):
    for book in catalog["liked"]:
        add_read_book(user_headers, book["id"])
    first = client.get("/api/v1/recommendations", headers=user_headers).json()["items"][0]
    client.post("/api/v1/recommendations/feedback", headers=user_headers, json={"recommendation_id": first["id"], "feedback": "not_helpful"})
    ids = [i["book"]["id"] for i in client.get("/api/v1/recommendations", headers=user_headers).json()["items"]]
    assert first["book"]["id"] not in ids


def test_llm_failure_does_not_break_recommendations(client, user_headers, catalog, add_read_book, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "openai_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "openai_base_url", "http://127.0.0.1:9/v1")  # порт закрыт -> сбой соединения
    monkeypatch.setattr(get_settings(), "openai_timeout", 0.5)
    monkeypatch.setattr(get_settings(), "openai_retries", 0)
    for book in catalog["liked"]:
        add_read_book(user_headers, book["id"])
    r = client.get("/api/v1/recommendations", headers=user_headers)
    assert r.status_code == 200 and r.json()["personalized"] is True
    assert r.json()["explanations"] is False and r.json()["items"]
