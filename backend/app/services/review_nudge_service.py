"""Review-nudge cron — the once-a-day job that asks recent customers who
tapped (earned a stamp) but never clicked the review button to leave a Google
review (Sprint 5, Feature 2).

Sibling of `reactivation_service`, deliberately structured the same way so the
two are easy to read side by side. The differences are intentional and live
in the policy constants and the detection step:

    reactivation  → customer inactive 30+ days        → "come back"
    review_nudge  → customer tapped 24h-7d ago,        → "leave us a review"
                    no review click since that tap

The cron endpoint (`routers/cron.py`) calls `run_daily(...)` once per day. This
module owns the policy and orchestration; it does NOT own HTTP concerns.

Channel note (umbrella spec, S5): the actual send goes through
`email_service.send_review_nudge`. Email ships today because business-initiated
WhatsApp needs a Meta-approved template and the Twilio Sandbox can't reach real
customers. When WhatsApp is approved, only the send seam changes — detection,
cooldown, and this orchestrator stay put.

Policy (hardcoded for v1, per-tenant config ships later — same call we made
for reactivation in S4-W2):
    NUDGE_AFTER_HOURS = 24  → don't pester someone who just visited
    LOOKBACK_DAYS     = 7   → ignore taps older than a week (no first-run flood)
    COOLDOWN_DAYS     = 30  → at most one nudge per customer per month
    PER_TENANT_LIMIT  = 500 → one big tenant can't monopolise a run

Failure & idempotency semantics mirror reactivation exactly: mark the cooldown
BEFORE the send, swallow per-customer errors, and rely on the cooldown so a
same-day re-run doesn't double-send.

Known limitation (accepted): we only know the customer didn't *click* the
review button (`action_taken='review_clicked'`), not whether they actually
posted on Google. The click is our proxy.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.config import get_settings
from app.db import customers, taps, tenants
from app.services import email_service

log = structlog.get_logger(__name__)


NUDGE_AFTER_HOURS = 24
LOOKBACK_DAYS = 7
COOLDOWN_DAYS = 30
PER_TENANT_LIMIT = 500


@dataclass
class TenantReviewNudgeResult:
    tenant_id: str
    # Customers the DB cleared to email (after gdpr/email/cooldown filters).
    eligible: int = 0
    # Emails actually attempted == rows where we wrote the cooldown marker.
    sent: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ReviewNudgeRunResult:
    tenants_scanned: int
    total_sent: int
    by_tenant: list[TenantReviewNudgeResult]


def _opt_out_url(magic_link_token: str) -> str:
    """Reuses the reactivation opt-out route (`/u/<token>`). Revoking consent
    there flips gdpr_consent=false, which stops BOTH reactivation and
    review-nudge — one opt-out covers all merchant-to-customer email."""
    base = get_settings().site_url.rstrip("/")
    return f"{base}/u/{magic_link_token}"


def _parse_ts(value: Any) -> datetime | None:
    """Parse a Supabase timestamp string into an aware UTC datetime.

    PostgREST returns ISO-8601, sometimes with a trailing 'Z' and sometimes
    with an explicit offset. `fromisoformat` handles offsets on 3.11; we
    normalise 'Z' first to be safe across PostgREST versions. Returns None for
    anything unparseable so a single bad row can't crash the whole run.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Treat naive timestamps as UTC — the DB stores UTC.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _candidate_customer_ids(
    signals: list[dict[str, Any]],
    *,
    lookback_since: datetime,
    nudge_before: datetime,
) -> list[str]:
    """Group raw tap signals per customer and return those who:
        - earned a stamp whose most recent occurrence is in
          [lookback_since, nudge_before], AND
        - have not clicked review at or after that stamp.

    `signals` are already restricted to this tenant, this window, the two
    relevant actions, and non-null customer_id (see taps.list_customer_review
    _signals). Grouping in Python keeps the rule readable and dodges fragile
    PostgREST NOT-EXISTS gymnastics; volumes are tiny.
    """
    last_stamp: dict[str, datetime] = {}
    last_review: dict[str, datetime] = {}

    for row in signals:
        cid = row.get("customer_id")
        action = row.get("action_taken")
        ts = _parse_ts(row.get("created_at"))
        if not isinstance(cid, str) or ts is None:
            continue
        if action == "stamp_earned":
            prev = last_stamp.get(cid)
            if prev is None or ts > prev:
                last_stamp[cid] = ts
        elif action == "review_clicked":
            prev = last_review.get(cid)
            if prev is None or ts > prev:
                last_review[cid] = ts

    candidates: list[str] = []
    for cid, stamp_at in last_stamp.items():
        # Most recent stamp must be old enough to nudge but inside the window.
        if not (lookback_since <= stamp_at <= nudge_before):
            continue
        reviewed_at = last_review.get(cid)
        # If they clicked review at/after that stamp, they're done — leave them.
        if reviewed_at is not None and reviewed_at >= stamp_at:
            continue
        candidates.append(cid)
    return candidates


def _process_tenant(
    tenant: dict[str, Any],
    *,
    lookback_since: datetime,
    nudge_before: datetime,
    cooldown_cutoff: datetime,
    now: datetime,
) -> TenantReviewNudgeResult:
    """All work for a single tenant. One customer's error never stops the
    rest — errors are collected for the cron caller to log."""
    tenant_id = tenant["id"]
    result = TenantReviewNudgeResult(tenant_id=tenant_id)

    review_url = (tenant.get("google_review_url") or "").strip()
    if not review_url:
        # Nothing to nudge toward — a tenant on the Loyalty-only path may have
        # no review URL configured. Skip the whole tenant cheaply.
        return result

    signals = taps.list_customer_review_signals(tenant_id, since=lookback_since)
    candidate_ids = _candidate_customer_ids(
        signals,
        lookback_since=lookback_since,
        nudge_before=nudge_before,
    )

    eligible = customers.find_review_nudge_eligible(
        tenant_id=tenant_id,
        customer_ids=candidate_ids,
        cooldown_cutoff=cooldown_cutoff,
        limit=PER_TENANT_LIMIT,
    )
    result.eligible = len(eligible)

    for customer in eligible:
        cid = customer.get("id")
        token = customer.get("magic_link_token")
        if not isinstance(cid, str) or not isinstance(token, str):
            # No magic token → can't render a working opt-out link. Skip
            # without marking, so it retries once the token is repaired.
            result.errors.append(f"customer {cid}: missing id or magic_link_token")
            continue

        try:
            # Mark FIRST (mark-before-send): a crash here costs this customer
            # one cycle, never a duplicate email.
            customers.mark_review_nudge_sent(cid, now)
            email_service.send_review_nudge(
                tenant=tenant,
                customer=customer,
                review_url=review_url,
                opt_out_url=_opt_out_url(token),
            )
            result.sent += 1
        except Exception as exc:
            log.exception(
                "review_nudge_customer_failed",
                tenant_id=tenant_id,
                customer_id=cid,
                error=str(exc),
            )
            result.errors.append(f"customer {cid}: {exc!s}")

    return result


def run_daily(*, now: datetime | None = None) -> ReviewNudgeRunResult:
    """Entry point invoked by the cron endpoint once per day.

    Accepts an explicit `now` for tests; defaults to wall-clock UTC.
    """
    current = now or datetime.now(UTC)
    nudge_before = current - timedelta(hours=NUDGE_AFTER_HOURS)
    lookback_since = current - timedelta(days=LOOKBACK_DAYS)
    cooldown_cutoff = current - timedelta(days=COOLDOWN_DAYS)

    active_tenants = tenants.list_active_for_cron()
    log.info(
        "review_nudge_run_start",
        tenants=len(active_tenants),
        nudge_before=nudge_before.isoformat(),
        lookback_since=lookback_since.isoformat(),
        cooldown_cutoff=cooldown_cutoff.isoformat(),
    )

    per_tenant: list[TenantReviewNudgeResult] = []
    total_sent = 0
    for tenant in active_tenants:
        tres = _process_tenant(
            tenant,
            lookback_since=lookback_since,
            nudge_before=nudge_before,
            cooldown_cutoff=cooldown_cutoff,
            now=current,
        )
        per_tenant.append(tres)
        total_sent += tres.sent

    log.info(
        "review_nudge_run_complete",
        tenants_scanned=len(active_tenants),
        total_sent=total_sent,
    )

    return ReviewNudgeRunResult(
        tenants_scanned=len(active_tenants),
        total_sent=total_sent,
        by_tenant=per_tenant,
    )
