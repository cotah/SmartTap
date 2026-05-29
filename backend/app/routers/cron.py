"""Cron-triggered endpoints.

These exist so an external scheduler (Vercel Cron, Railway Scheduler, plain
cURL from cron-job.org) can poke the backend on a schedule. The backend
itself doesn't run any background loops — keeping the API stateless makes
horizontal scaling and Railway's zero-downtime deploys trivial.

Auth model: a single shared secret in `CRON_TOKEN`. The scheduler sends it
as the `X-Cron-Token` header. The endpoint:
    - Returns 503 if `CRON_TOKEN` isn't configured (so a misconfigured env
      can't get accidentally triggered with no auth at all).
    - Returns 401 on mismatch — using a constant-time compare to avoid
      timing oracles, even though the token is short.

The endpoints are deliberately POST (not GET) so naïve crawlers or browser
prefetchers can't trigger expensive work.
"""

import hmac

import structlog
from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.services import (
    monthly_email_service,
    reactivation_service,
    review_nudge_service,
    review_response_service,
)

router = APIRouter(tags=["cron"])
log = structlog.get_logger(__name__)


def _verify_cron_token(provided: str | None) -> None:
    settings = get_settings()
    expected = settings.cron_token
    if not expected:
        # Fail closed in unconfigured envs. The alternative (allow when empty)
        # would mean a forgotten env var silently opens the door.
        raise HTTPException(status_code=503, detail="Cron not configured")
    if not provided or not hmac.compare_digest(provided, expected):
        # No need to differentiate "missing" vs "wrong" in the response — both
        # leak the same bit and give an attacker the same hint.
        raise HTTPException(status_code=401, detail="Invalid cron token")


@router.post("/cron/reactivation")
def trigger_reactivation(
    x_cron_token: str | None = Header(default=None, alias="X-Cron-Token"),
) -> dict[str, int]:
    """Daily reactivation pass.

    Idempotent: calling twice in the same day re-runs the scan, but the
    per-customer cooldown (90 days) prevents duplicate emails. Safe to retry
    after a partial run.

    Returns aggregate counters only — per-tenant breakdown stays in logs to
    avoid leaking tenant ids in case the cron URL ever gets curl'd from
    outside the scheduler.
    """
    _verify_cron_token(x_cron_token)

    result = reactivation_service.run_daily()
    return {
        "tenants_scanned": result.tenants_scanned,
        "total_sent": result.total_sent,
    }


@router.post("/cron/review-nudge")
def trigger_review_nudge(
    x_cron_token: str | None = Header(default=None, alias="X-Cron-Token"),
) -> dict[str, int]:
    """Daily review-nudge pass (S5 Feature 2).

    Idempotent: re-running the same day re-scans, but the per-customer cooldown
    (30 days) prevents duplicate emails. Safe to retry after a partial run.

    Returns aggregate counters only — per-tenant breakdown stays in logs so a
    leaked cron URL can't surface tenant ids.
    """
    _verify_cron_token(x_cron_token)

    result = review_nudge_service.run_daily()
    return {
        "tenants_scanned": result.tenants_scanned,
        "total_sent": result.total_sent,
    }


@router.post("/cron/review-responses")
def trigger_review_responses(
    x_cron_token: str | None = Header(default=None, alias="X-Cron-Token"),
) -> dict[str, int]:
    """Daily pass that fetches new Google reviews and drafts replies (S5 F3).

    Idempotent: the (tenant, google_review_id) dedupe means re-running won't
    re-draft a review already stored. No-op when no tenant has connected Google
    or the API isn't live yet.
    """
    _verify_cron_token(x_cron_token)

    result = review_response_service.run_daily()
    return {
        "tenants_scanned": result.tenants_scanned,
        "reviews_drafted": result.reviews_drafted,
    }


@router.post("/cron/monthly-report")
def trigger_monthly_report(
    x_cron_token: str | None = Header(default=None, alias="X-Cron-Token"),
    year: int | None = None,
    month: int | None = None,
) -> dict[str, int]:
    """Monthly report pass — meant to run on the 1st of each Dublin month.

    With no query params, the run targets the previous complete Dublin month
    (so a run at 06:30 IST on May 1 reports April). The optional `year`/`month`
    pair lets ops trigger a back-fill or a re-send for a specific month
    without redeploying — pass them together or omit both.

    Not idempotent on its own: a second call same-day will re-send. Keep the
    scheduler set to fire exactly once per month; ops can manually re-fire
    when they're sure the previous run failed.
    """
    _verify_cron_token(x_cron_token)

    result = monthly_email_service.run_monthly(year=year, month=month)
    return {
        "year": result.year,
        "month": result.month,
        "tenants_scanned": result.tenants_scanned,
        "total_sent": result.total_sent,
    }
