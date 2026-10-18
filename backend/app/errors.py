from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "BAD_REQUEST"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "") or request.headers.get("x-request-id", "")


def error_body(request: Request, code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id_of(request)}}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_body(request, exc.code, exc.message))


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    if exc.status_code == 401:
        code = "UNAUTHORIZED"
    if exc.status_code == 403:
        code = "FORBIDDEN"
    return JSONResponse(status_code=exc.status_code, content=error_body(request, code, detail))


async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body(request, "VALIDATION_ERROR", "Please check the highlighted fields and try again"),
    )


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_body(request, "INTERNAL_ERROR", "Something went wrong. Please try again."),
    )
