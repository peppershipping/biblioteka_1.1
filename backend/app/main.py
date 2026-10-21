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


@asynccontextmanager
async def lifespan(_: FastAPI):
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
