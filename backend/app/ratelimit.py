"""
Rate limiting (ТЗ 15.3): ~100 запросов/мин на IP, строже — для login/register.
Счётчики в Redis (общие для всех экземпляров backend); без Redis — в памяти процесса.
"""

from fastapi import Depends, HTTPException, Request

from . import cache
from .config import get_settings
from .ratelimit_core import MemoryRateLimiter

_memory = MemoryRateLimiter()
WINDOW_SECONDS = 60


def reset_memory_limiter() -> None:  # используется в тестах
    _memory.reset()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check(scope: str, limit: int, request: Request) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    key = f"rl:{scope}:{_client_ip(request)}"
    count = cache.incr_with_ttl(key, WINDOW_SECONDS)
    if count is not None:
        allowed, retry_after = count <= limit, WINDOW_SECONDS
    else:
        allowed, retry_after = _memory.hit(key, limit, WINDOW_SECONDS)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Слишком много запросов. Повторите попытку позже.",
            headers={"Retry-After": str(retry_after)},
        )


def default_limit(request: Request) -> None:
    """Общий лимит на IP для всех обычных маршрутов."""
    _check("api", get_settings().rate_limit_default, request)


def auth_limit(request: Request) -> None:
    """Строгий лимит для login / register / refresh."""
    _check("auth", get_settings().rate_limit_auth, request)


DefaultLimit = Depends(default_limit)
AuthLimit = Depends(auth_limit)
