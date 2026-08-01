import logging

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import BusinessError
from app.routers import (
    billing,
    campaigns,
    cron,
    customers,
    dashboard,
    google_oauth,
    health,
    me,
    nfc_tags,
    onboarding,
    reports,
    reviews,
    rewards,
    segments,
    taps,
    tenants,
    webhooks,
)

# Routes whose URL carries a secret. The uvicorn access log (and, via Sentry's
# logging integration, error-event breadcrumbs) records the full request line,
# so these get their sensitive part masked before any handler sees them.
_OPT_OUT_PREFIX = "/v1/customers/opt-out/"
_GOOGLE_CALLBACK = "/v1/google/callback"


def _redact_access_path(path: str) -> str:
    if path.startswith(_OPT_OUT_PREFIX):
        # The magic-link token is a permanent customer credential.
        return _OPT_OUT_PREFIX + "[redacted]"
    if path.startswith(_GOOGLE_CALLBACK) and "?" in path:
        # Query carries the OAuth authorization code + signed state.
        return _GOOGLE_CALLBACK + "?[redacted]"
    return path


class _RedactAccessLog(logging.Filter):
    """Mask secret-bearing URLs in uvicorn access-log lines.

    We deliberately keep the access log on (it's our only per-request
    delivery trace — e.g. how missing Meta webhooks were diagnosed) and
    redact instead of dropping lines. uvicorn.access records carry
    args = (client_addr, method, full_path, http_version, status_code).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) == 5 and isinstance(args[2], str):
            redacted = _redact_access_path(args[2])
            if redacted != args[2]:
                record.args = (args[0], args[1], redacted, args[3], args[4])
        return True


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=level)
    # httpx/httpcore log full request URLs at INFO, and the Meta + Google
    # clients carry client_secret / access_token in query params — never let
    # those reach the logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # stripe logs request payloads at DEBUG and urllib3 gets similarly verbose
    # — pin them so a LOG_LEVEL=DEBUG incident-debugging session can't leak
    # payment payloads into Railway logs.
    logging.getLogger("stripe").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").addFilter(_RedactAccessLog())
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            # Railway's log viewer displays the `message` field of JSON log
            # lines — structlog's default `event` key renders as a blank line.
            structlog.processors.EventRenamer("message"),
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
            # Never attach request bodies to events — identify/identify-verify
            # bodies carry phone numbers and live OTP codes, and Sentry's
            # default scrubber doesn't cover `phone`/`code` keys.
            max_request_body_size="never",
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
    app.include_router(onboarding.router, prefix="/v1")
    app.include_router(billing.router, prefix="/v1")
    app.include_router(campaigns.router, prefix="/v1")
    app.include_router(cron.router, prefix="/v1")
    app.include_router(reports.router, prefix="/v1")
    app.include_router(segments.router, prefix="/v1")
    app.include_router(nfc_tags.router, prefix="/v1")
    app.include_router(reviews.router, prefix="/v1")
    app.include_router(google_oauth.router, prefix="/v1")

    return app


app = create_app()
