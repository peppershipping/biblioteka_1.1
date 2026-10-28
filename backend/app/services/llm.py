"""
Внешняя языковая модель через API, совместимый с Chat Completions (ТЗ раздел 9).

Модель НЕ участвует в подборе книг — только формулирует пояснения и (по
желанию) разбирает поисковый запрос. Любой сбой (таймаут, 5xx, неверный
ответ, отсутствие ключа) возвращает None, и приложение работает дальше без
пояснений (ТЗ 15.1 правило 37). Ключ и тексты запросов в журнал не пишутся.
"""

import json
import logging
import re

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def _chat(system: str, user: str, max_tokens: int = 700) -> str | None:
    settings = get_settings()
    if not settings.llm_enabled:
        return None
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.openai_model,
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    for attempt in range(settings.openai_retries + 1):
        try:
            with httpx.Client(timeout=settings.openai_timeout) as client:
                response = client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            if response.status_code < 500 and response.status_code != 429:
                logger.warning("LLM отклонила запрос: HTTP %s", response.status_code)
                return None
            logger.warning("LLM временно недоступна: HTTP %s (попытка %s)", response.status_code, attempt + 1)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            logger.warning("Сбой обращения к LLM (попытка %s): %s", attempt + 1, type(exc).__name__)
    return None


def _parse_json_object(text: str | None) -> dict | None:
    if not text:
        return None
    match = _JSON_OBJECT.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def explain(liked_titles: list[str], items: list[dict]) -> dict[int, str] | None:
    """
    items: [{'book_id', 'title', 'authors', 'genres', 'similar_to'}].
    Возвращает {book_id: краткое пояснение} или None, если модель недоступна.
    """
    if not items:
        return {}
    lines = [
        f"- id={it['book_id']}: «{it['title']}», авторы: {', '.join(it['authors']) or '—'}, "
        f"жанры: {', '.join(it['genres']) or '—'}"
        + (f", похожа на «{it['similar_to']}»" if it.get("similar_to") else "")
        for it in items
    ]
    prompt = (
        f"Читателю понравились книги: {'; '.join(liked_titles) or '—'}.\n"
        "Для каждой книги из списка напиши ОДНО короткое предложение на русском (до 25 слов) — "
        "почему она может ему понравиться. Верни только JSON-объект вида "
        '{"<id>": "пояснение"}.\n' + "\n".join(lines)
    )
    data = _parse_json_object(
        _chat("Ты помощник книжного сервиса. Отвечай строго JSON-объектом без пояснений.", prompt)
    )
    if data is None:
        return None
    allowed = {it["book_id"] for it in items}
    result: dict[int, str] = {}
    for key, value in data.items():
        if str(key).isdigit() and int(key) in allowed and isinstance(value, str) and value.strip():
            result[int(key)] = value.strip()[:300]
    return result or None


def interpret_query(query: str, genres: list[str]) -> dict | None:
    """
    «Умный поиск»: превращает запрос на естественном языке в параметры поиска
    {'q': str, 'genre': str|None, 'year': int|None}. Жанр проверяется по реальному
    списку жанров каталога.
    """
    prompt = (
        f"Доступные жанры: {', '.join(genres[:100]) or '—'}.\n"
        f"Запрос читателя: «{query[:200]}».\n"
        'Верни только JSON {"q": "ключевые слова для поиска", "genre": "жанр из списка или null", '
        '"year": год публикации числом или null}.'
    )
    data = _parse_json_object(_chat("Ты разбираешь поисковые запросы книжного сервиса.", prompt, 200))
    if data is None:
        return None
    result: dict = {"q": None, "genre": None, "year": None}
    q = data.get("q")
    if isinstance(q, str) and q.strip():
        result["q"] = q.strip()[:100]
    genre = data.get("genre")
    if isinstance(genre, str):
        matched = next((g for g in genres if g.lower() == genre.strip().lower()), None)
        result["genre"] = matched
    year = data.get("year")
    if isinstance(year, int) and not isinstance(year, bool) and 1 <= year <= 2100:
        result["year"] = year
    return result if any(result.values()) else None
