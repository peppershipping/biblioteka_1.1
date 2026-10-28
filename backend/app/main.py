"""
Точка входа FastAPI.

API доступно по /api/v1/... (версионированный префикс, ТЗ 17) и по /api/...
(алиас без версии из раздела 8 ТЗ; в документацию не попадает). Служебные
маршруты: /health (проверка живости), /metrics (Prometheus — снаружи не
проксируется nginx), /docs, /redoc, /openapi.json (отключаются DOCS_ENABLED=false).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import get_settings
from .errors import register_error_handlers
from .logging_config import setup_logging
from .middleware import ObservabilityMiddleware
from .routers import auth, books, health, library, ratings, recommendations
from .services import bootstrap

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

TAGS = [
    {"name": "Аутентификация", "description": "Регистрация, вход, обновление и отзыв токенов"},
    {"name": "Книги", "description": "Каталог, поиск и фильтрация; добавление книг — только admin"},
    {"name": "Личная библиотека", "description": "Книги пользователя и статусы чтения"},
    {"name": "Оценки", "description": "Оценка по трём критериям и итоговая оценка"},
    {"name": "Рекомендации", "description": "Персональные рекомендации и обратная связь"},
    {"name": "Служебные", "description": "Проверка работоспособности"},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        bootstrap.run()
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось выполнить начальную загрузку данных (выполнены ли миграции?)")
        raise
    yield


app = FastAPI(
    title="Библиотека — REST API",
    description="Персональный читательский дневник: библиотека, оценки по трём критериям, рекомендации.",
    version="3.0.0",
    openapi_tags=TAGS,
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

# Порядок важен: последний добавленный — самый внешний. CORS снаружи, чтобы
# заголовки CORS были и у ответов с ошибками.
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,  # белый список; "*" отбрасывается
    allow_credentials=False,                  # токены передаются заголовком Authorization, не cookie
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Retry-After"],
)

register_error_handlers(app)

API_ROUTERS = [
    auth.router,
    books.router,
    books.genres_router,
    library.router,
    ratings.router,
    recommendations.router,
    health.router,
]
for prefix, in_schema in (("/api/v1", True), ("/api", False)):
    for api_router in API_ROUTERS:
        app.include_router(api_router, prefix=prefix, include_in_schema=in_schema)

app.include_router(health.router, include_in_schema=False)  # /health — для Docker и мониторинга


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
