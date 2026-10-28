<<<<<<< HEAD
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
=======
"""Точка входа FastAPI: подключает роутеры, CORS, создаёт таблицы."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from . import models  # noqa: F401 — регистрирует модели в metadata
from .config import get_settings
from .database import Base, engine
from .routers import auth, books, library, ratings

settings = get_settings()


def apply_light_migrations() -> None:
    """
    Учебный проект без Alembic: create_all создаёт только отсутствующие таблицы,
    а новые колонки в уже существующих таблицах добавляем вручную и идемпотентно.
    """
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE user_books ADD COLUMN IF NOT EXISTS comment TEXT NOT NULL DEFAULT ''")
        )
>>>>>>> 088ebc434e4e609566051a7126e169906afacece


@asynccontextmanager
async def lifespan(_: FastAPI):
<<<<<<< HEAD
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
=======
    Base.metadata.create_all(bind=engine)
    apply_light_migrations()
    yield


app = FastAPI(title="Библиотека API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Единый формат ошибок: {"error": {"code": ..., "message": ...}}
@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = {"error": detail}
    else:
        body = {"error": {"code": "error", "message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    fields = [
        {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Проверьте корректность введённых данных.",
                "details": fields,
            }
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


for router_module in (auth, books, library, ratings):
    app.include_router(router_module.router)
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
