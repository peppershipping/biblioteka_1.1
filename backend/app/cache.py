"""
Необязательный кэш на Redis (ТЗ 15.4). Кэш НЕ является источником истины:
если Redis не настроен или недоступен, все операции тихо превращаются в «нет
значения», а данные читаются из PostgreSQL.
"""

import json
import logging
import time

from .config import get_settings

logger = logging.getLogger(__name__)

_client = None
_disabled_until = 0.0
RETRY_AFTER_FAILURE = 15  # секунд, в течение которых Redis не опрашиваем после сбоя


def _get_client():
    global _client, _disabled_until
    settings = get_settings()
    if not settings.redis_url or time.monotonic() < _disabled_until:
        return None
    if _client is None:
        import redis  # импорт здесь: без REDIS_URL модуль redis не нужен

        _client = redis.Redis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=0.3, socket_timeout=0.3
        )
    return _client


def _failed(exc: Exception) -> None:
    global _disabled_until
    _disabled_until = time.monotonic() + RETRY_AFTER_FAILURE
    logger.warning("Redis недоступен, кэш отключён на %s с: %s", RETRY_AFTER_FAILURE, type(exc).__name__)


def get_json(key: str):
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:  # noqa: BLE001 — любой сбой кэша не должен ломать запрос
        _failed(exc)
        return None


def set_json(key: str, value, ttl: int) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
    except Exception as exc:  # noqa: BLE001
        _failed(exc)


def version(namespace: str) -> int:
    """Номер версии пространства имён: меняется при инвалидации, входит в ключи кэша."""
    client = _get_client()
    if client is None:
        return 0
    try:
        raw = client.get(f"ver:{namespace}")
        return int(raw) if raw else 0
    except Exception as exc:  # noqa: BLE001
        _failed(exc)
        return 0


def bump(namespace: str) -> None:
    """Инвалидация: после увеличения версии старые ключи перестают использоваться."""
    client = _get_client()
    if client is None:
        return
    try:
        client.incr(f"ver:{namespace}")
    except Exception as exc:  # noqa: BLE001
        _failed(exc)


def incr_with_ttl(key: str, ttl: int) -> int | None:
    """Счётчик для rate limiting. None — Redis недоступен (используем память процесса)."""
    client = _get_client()
    if client is None:
        return None
    try:
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl, nx=True)
        count, _ = pipe.execute()
        return int(count)
    except Exception as exc:  # noqa: BLE001
        _failed(exc)
        return None
