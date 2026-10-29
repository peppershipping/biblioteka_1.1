
"""FastAPI application entry point."""

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
    {
        "name": "Аутентификация",
        "description": "Регистрация, вход, обновление и отзыв токенов",
    },
    {
        "name": "Книги",
        "description": "Каталог, поиск и фильтрация; добавление книг — только admin",
    },
    {
        "name": "Личная библиотека",
        "description": "Книги пользователя и статусы чтения",
    },
    {
        "name": "Оценки",
        "description": "Оценка по трём критериям и итоговая оценка",
    },
    {
        "name": "Рекомендации",
        "description": "Персональные рекомендации и обратная связь",
    },
    {
        "name": "Служебные",
        "description": "Проверка работоспособности",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        bootstrap.run()
    except Exception:
        logger.exception(
            "Не удалось выполнить начальную загрузку данных. "
            "Проверьте, применены ли миграции."
        )
        raise

    yield


app = FastAPI(
    title="Библиотека — REST API",
    description=(
        "Персональный читательский дневник: библиотека, "
        "оценки по трём критериям, рекомендации."
    ),
    version="3.0.0",
    openapi_tags=TAGS,
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

# Порядок middleware важен: CORS должен добавлять заголовки и к ответам с ошибками.
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
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

# Версионированный API и совместимый алиас без версии.
for prefix, in_schema in (("/api/v1", True), ("/api", False)):
    for api_router in API_ROUTERS:
        app.include_router(
            api_router,
            prefix=prefix,
            include_in_schema=in_schema,
        )

# Отдельный health endpoint для Docker и мониторинга.
app.include_router(health.router, include_in_schema=False)


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
