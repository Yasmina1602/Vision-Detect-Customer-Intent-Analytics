"""Yagona xato formati: {"error": {"code", "message", "request_id"}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, extra: dict | None = None):
        self.code, self.message, self.status, self.extra = code, message, status, extra or {}
        super().__init__(message)


class NotFound(AppError):
    def __init__(self, message: str = "Topilmadi"):
        super().__init__("NOT_FOUND", message, 404)


class Forbidden(AppError):
    def __init__(self, message: str = "Ruxsat yo'q"):
        super().__init__("FORBIDDEN", message, 403)


class Unauthorized(AppError):
    def __init__(self, message: str = "Avtorizatsiya talab qilinadi"):
        super().__init__("UNAUTHORIZED", message, 401)


def _body(request: Request, code: str, message: str, extra: dict | None = None) -> dict:
    err = {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None)}
    if extra:
        err.update(extra)
    return {"error": err}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return JSONResponse(_body(request, exc.code, exc.message, exc.extra), status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED",
                429: "RATE_LIMITED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(_body(request, code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        fields = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return JSONResponse(_body(request, "VALIDATION_ERROR", "So'rov ma'lumotlari noto'g'ri", {"fields": fields}),
                            status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("Kutilmagan xato", extra={"request_id": getattr(request.state, "request_id", None)})
        return JSONResponse(_body(request, "INTERNAL_ERROR", "Ichki xatolik yuz berdi"), status_code=500)
