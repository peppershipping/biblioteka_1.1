"""
Сквозная обработка запросов: request_id, заголовки безопасности, метрики
Prometheus (время ответа, RPS, ошибки — ТЗ 13.2 «Наблюдаемость») и журнал доступа.
"""

import logging
import re
import time
import uuid

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .logging_config import request_id_var

logger = logging.getLogger("app.access")

REQUESTS = Counter("http_requests_total", "Количество HTTP-запросов", ["method", "path", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Время обработки запроса",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.3, 0.5, 1.0, 2.5, 5.0),
)

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9\-]{8,64}$")
SKIP_ACCESS_LOG = {"/health", "/api/health", "/api/v1/health", "/metrics"}


def _route_template(request: Request) -> str:
    """Шаблон маршрута (/books/{book_id}), а не реальный путь — чтобы не раздувать метрики."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            if request.url.path.startswith("/api"):
                response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            elapsed = time.perf_counter() - started
            path = _route_template(request)
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(request.method, path).observe(elapsed)
            if request.url.path not in SKIP_ACCESS_LOG:
                logger.info("%s %s -> %s (%.0f мс)", request.method, request.url.path, status, elapsed * 1000)
            request_id_var.reset(token)
