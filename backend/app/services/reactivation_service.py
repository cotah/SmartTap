"""Reactivation cron — the once-a-day job that nudges dormant customers.

The cron endpoint (`routers/cron.py`) calls `run_daily(...)` once per day.
This module owns the policy (what counts as dormant, how often to re-email)
and orchestrates the per-tenant work; it does NOT own HTTP concerns.

Policy (deliberately hardcoded for S4-W2 — per-tenant config ships later):
    INACTIVE_AFTER_DAYS = 30  → only customers who haven't visited in 30+ days
    COOLDOWN_DAYS = 90        → never re-email the same customer within 90 days

Failure semantics:
    - We mark `last_reactivation_sent_at` BEFORE the actual email send. If the
      cron crashes mid-loop, the next run skips this customer (re-emailing in
      89 days instead of the next day). Worst case: a customer misses one
      cycle. Far better than spamming them.
    - Email send failures are swallowed by email_service (Resend down ≠ cron
      failure). The mark stays, so the next run still respects the cooldown.

Idempotency:
    - Calling `run_daily` twice in the same day is safe — the cooldown check
      prevents double-emails. We rely on this when re-running after partial
      failures.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.config import get_settings
from app.db import customers, tenants
from app.errors import NotFoundError
from app.services import email_service

log = structlog.get_logger(__name__)


INACTIVE_AFTER_DAYS = 30
COOLDOWN_DAYS = 90

# Cap per-tenant batch so one big tenant can't monopolise a cron run. At 500
# the run still finishes in well under a minute even with Resend latency, and
# the next day picks up the remainder for tenants that have a bigger backlog.
PER_TENANT_LIMIT = 500


@dataclass
class TenantReactivationResult:
    tenant_id: str
    # Number of dormant customers considered after filters; useful for
    # debugging when a tenant reports "I expected my customers to get emails".
    eligible: int = 0
    # Number of emails actually attempted (== rows where we wrote the cooldown
    # marker). May be less than `eligible` only if a per-customer error fired
    # before we attempted send — currently that's never, but keep the counter
    # split for forward-compat.
    sent: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ReactivationRunResult:
    tenants_scanned: int
    total_sent: int
    by_tenant: list[TenantReactivationResult]


def _opt_out_url(magic_link_token: str) -> str:
    base = get_settings().site_url.rstrip("/")
    return f"{base}/u/{magic_link_token}"


def _magic_link_url(magic_link_token: str) -> str:
    """Same shape as customer self-serve magic links. The /m route on web
    reads the token and seeds the cookie for the next /t/[uuid] tap; for
    standalone "show my stamps" use we can land them on the same place.

    Today the web side has the magic token cookie set on /t/[uuid] via
    `readMagicToken`. We pass the same token here; the page renders the
    customer's progress without needing a tap event.
    """
    base = get_settings().site_url.rstrip("/")
    return f"{base}/m/{magic_link_token}"


def _process_tenant(
    tenant: dict[str, Any],
    *,
    inactive_cutoff: datetime,
    cooldown_cutoff: datetime,
    now: datetime,
) -> TenantReactivationResult:
    """All work for a single tenant. Errors on one customer don't stop the
    rest — they're collected into `errors` for the cron caller to log."""
    tenant_id = tenant["id"]
    result = TenantReactivationResult(tenant_id=tenant_id)

    eligible = customers.find_inactive_for_reactivation(
        tenant_id=tenant_id,
        inactive_cutoff=inactive_cutoff,
        cooldown_cutoff=cooldown_cutoff,
        limit=PER_TENANT_LIMIT,
    )
    result.eligible = len(eligible)

    for customer in eligible:
        cid = customer.get("id")
        token = customer.get("magic_link_token")
        if not isinstance(cid, str) or not isinstance(token, str):
            # Defensive: a customer row missing the magic token can't get a
            # working "show my stamps" link, so skip rather than send a
            # broken email.
            result.errors.append(f"customer {cid}: missing id or magic_link_token")
            continue

        try:
            # Mark FIRST so a crash here doesn't cause a duplicate email on
            # the next run. The downside (missed cycle on Resend outage) is
            # the lesser evil.
            customers.mark_reactivation_sent(cid, now)
            email_service.send_reactivation(
                tenant=tenant,
                customer=customer,
                magic_link_url=_magic_link_url(token),
                opt_out_url=_opt_out_url(token),
            )
            result.sent += 1
        except Exception as exc:
            # Log but keep iterating. The marker is already written, so this
            # customer won't be retried for 90 days regardless — that's
            # intentional, matches the "mark-before-send" contract.
            log.exception(
                "reactivation_customer_failed",
                tenant_id=tenant_id,
                customer_id=cid,
                error=str(exc),
            )
            result.errors.append(f"customer {cid}: {exc!s}")

    return result


def run_daily(*, now: datetime | None = None) -> ReactivationRunResult:
    """Entry point invoked by the cron endpoint once per day.

    Accepts an explicit `now` for tests; defaults to wall-clock UTC.
    """
    current = now or datetime.now(UTC)
    inactive_cutoff = current - timedelta(days=INACTIVE_AFTER_DAYS)
    cooldown_cutoff = current - timedelta(days=COOLDOWN_DAYS)

    active_tenants = tenants.list_active_for_cron()
    log.info(
        "reactivation_run_start",
        tenants=len(active_tenants),
        inactive_cutoff=inactive_cutoff.isoformat(),
        cooldown_cutoff=cooldown_cutoff.isoformat(),
    )

    per_tenant: list[TenantReactivationResult] = []
    total_sent = 0
    for tenant in active_tenants:
        tres = _process_tenant(
            tenant,
            inactive_cutoff=inactive_cutoff,
            cooldown_cutoff=cooldown_cutoff,
            now=current,
        )
        per_tenant.append(tres)
        total_sent += tres.sent

    log.info(
        "reactivation_run_complete",
        tenants_scanned=len(active_tenants),
        total_sent=total_sent,
    )

    return ReactivationRunResult(
        tenants_scanned=len(active_tenants),
        total_sent=total_sent,
        by_tenant=per_tenant,
    )


def opt_out(magic_link_token: str) -> None:
    """Public, idempotent GDPR opt-out triggered from the email footer link.

    Raises NotFoundError when the token doesn't match any customer — the
    router translates this into a generic 404 so we never leak whether a
    given token is valid (would otherwise enable enumeration).
    """
    row = customers.revoke_consent_via_magic_token(magic_link_token)
    if row is None:
        raise NotFoundError("Unknown opt-out token")
    log.info("reactivation_opt_out", customer_id=row.get("id"))
