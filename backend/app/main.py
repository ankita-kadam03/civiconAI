from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.db import database
from app.errors import AppError, app_error_handler, http_error_handler, unhandled_handler, validation_handler
from app.rate_limit import limiter
from app.routers import admin, ai, auth, complaints, internal, notifications, public, users, v1
from app.seed import seed_if_needed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("civicon")
MAX_BODY_BYTES = 12 * 1024 * 1024


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    database.connect()
    seed_if_needed(database)
    from app.services.ai import ai_service
    from app.services.bigquery_analytics import bigquery_analytics
    from app.services.integrations_check import assert_required_integrations

    ai_service.reload_from_settings()
    bigquery_analytics.connect()
    warnings = assert_required_integrations(strict=settings.integration_startup_strict)
    for w in warnings:
        log.error("integration_startup %s", w)
    try:
        n = bigquery_analytics.backfill_from_db(database)
        if n:
            log.info("bigquery_backfill rows=%s", n)
    except Exception as exc:  # noqa: BLE001
        log.warning("bigquery_backfill_failed error=%s", type(exc).__name__)
    log.info(
        "civicon_started memory_db=%s db=%s fresh=%s ai=%s bq=%s",
        settings.allow_memory_db,
        database.mode,
        settings.fresh_start,
        __import__("app.services.ai", fromlist=["ai_service"]).ai_service.mode,
        bigquery_analytics.health().get("status"),
    )
    yield
    database.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Civicon AI API",
        description="Civic issue reporting and escalation. Your Neighbourhood. Your Voice.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(Exception, unhandled_handler)

    @app.middleware("http")
    async def correlation(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=413,
                content={"error": {"code": "PAYLOAD_TOO_LARGE", "message": "Request is too large", "request_id": rid}},
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        log.info(
            "request method=%s path=%s status=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            rid,
        )
        return response

    app.include_router(public.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(complaints.router)
    app.include_router(notifications.router)
    app.include_router(ai.router)
    app.include_router(admin.router)
    app.include_router(v1.router)
    app.include_router(internal.router)
    return app


app = create_app()
