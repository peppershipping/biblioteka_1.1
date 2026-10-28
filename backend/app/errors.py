"""
Единый формат ошибок (ТЗ 17.1): {"detail": "Описание ошибки"}.
Для 422 дополнительно возвращается список полей. Стек вызовов, SQL и внутренние
пути клиенту не отдаются — подробности пишутся в журнал с request_id.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .validation_messages import format_errors, summarize

logger = logging.getLogger(__name__)

_DEFAULT_TEXTS = {
    401: "Требуется авторизация",
    403: "Недостаточно прав",
    404: "Ресурс не найден",
    405: "Метод не поддерживается",
    409: "Конфликт данных",
    429: "Слишком много запросов. Повторите попытку позже.",
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) and exc.detail not in {
            "Not Found", "Method Not Allowed", "Forbidden", "Unauthorized", "Not authenticated"
        } else _DEFAULT_TEXTS.get(exc.status_code, "Ошибка запроса")
        return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = format_errors(list(exc.errors()))
        return JSONResponse({"detail": summarize(errors), "errors": errors}, status_code=422)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        logger.exception("Необработанная ошибка (request_id=%s)", request_id)
        return JSONResponse(
            {"detail": "Внутренняя ошибка сервера", "request_id": request_id}, status_code=500
        )
