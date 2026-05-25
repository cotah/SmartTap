import logging

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import BusinessError
from app.routers import (
    customers,
    dashboard,
    health,
    me,
    rewards,
    taps,
    tenants,
    webhooks,
)


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=level)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings.log_level)

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.1,
        )

    app = FastAPI(
        title="SmartTap API",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(BusinessError)
    async def handle_business_error(_request: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "detail": exc.detail,
                }
            },
        )

    app.include_router(health.router)
    app.include_router(taps.router, prefix="/v1")
    app.include_router(customers.router, prefix="/v1")
    app.include_router(tenants.router, prefix="/v1")
    app.include_router(rewards.router, prefix="/v1")
    app.include_router(webhooks.router, prefix="/v1")
    app.include_router(me.router, prefix="/v1")
    app.include_router(dashboard.router, prefix="/v1")

    return app


app = create_app()
