"""Monthly report cron orchestrator (S4-W3).

Once per Dublin month — typically the cron is wired up for the 1st at 06:30
local — this module computes the previous month's report for every active
tenant, renders it as a PDF, and emails it to the owner with the PDF
attached.

Design choices:

    - Mirrors `reactivation_service.run_daily` so the cron caller pattern is
      uniform: build an "active tenants" list, loop, capture per-tenant errors,
      log aggregate counters.
    - No persistence. A second run on the same day will re-send the email.
      That's intentional for the MVP — a per-tenant `monthly_reports` table
      adds operational weight that isn't justified yet. Operators triggering
      the cron manually should be aware (the cron endpoint stays
      idempotency-free for the same reason).
    - Period selection always uses "previous complete Dublin month" relative
      to `now`. The endpoint can override `year`/`month` for back-fills if a
      run is missed, but the cron entrypoint never has to.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from app.db import tenants
from app.errors import NotFoundError
from app.services import email_service, monthly_report_service, pdf_renderer

log = structlog.get_logger(__name__)


@dataclass
class TenantMonthlyResult:
    tenant_id: str
    # `True` when send was attempted (Resend may still no-op in dev — that
    # counts as attempted because the code path executed). `False` only when
    # we skipped before reaching the email layer (e.g. tenant disappeared).
    sent: bool = False
    error: str | None = None


@dataclass
class MonthlyRunResult:
    year: int
    month: int
    tenants_scanned: int
    total_sent: int
    by_tenant: list[TenantMonthlyResult] = field(default_factory=list)


def _process_tenant(
    tenant_row: dict,  # type: ignore[type-arg]
    *,
    year: int,
    month: int,
) -> TenantMonthlyResult:
    """Compute + render + send for ONE tenant.

    Errors are caught and returned in the result, never raised — the cron
    must finish the loop even if one tenant blows up. The tenant id is the
    only guaranteed field; everything else we look up via
    `monthly_report_service.compute` so the report sees the full tenant row,
    not just the cron's lightweight selection.
    """
    tenant_id = str(tenant_row.get("id") or "")
    result = TenantMonthlyResult(tenant_id=tenant_id)
    if not tenant_id:
        result.error = "missing tenant id"
        return result

    try:
        report = monthly_report_service.compute(
            tenant_id=tenant_id, year=year, month=month
        )
    except NotFoundError:
        # Tenant existed when list_active_for_cron ran but got deleted before
        # we got to it. Skip silently — not a real error worth surfacing.
        result.error = "tenant disappeared mid-run"
        return result
    except Exception as exc:
        log.exception(
            "monthly_report_compute_failed", tenant_id=tenant_id, error=str(exc)
        )
        result.error = f"compute: {exc!s}"
        return result

    try:
        pdf_bytes = pdf_renderer.render_monthly_report(report)
        filename = pdf_renderer.report_filename(report)
    except Exception as exc:
        log.exception(
            "monthly_report_render_failed", tenant_id=tenant_id, error=str(exc)
        )
        result.error = f"render: {exc!s}"
        return result

    # email_service swallows Resend failures itself, so this never raises
    # under normal operation. Wrap defensively anyway — the contract is
    # "loop must finish", and a regression in the email layer shouldn't be
    # able to break it.
    try:
        email_service.send_monthly_report(
            tenant_id=tenant_id,
            tenant=report.tenant,
            year=year,
            month=month,
            pdf_bytes=pdf_bytes,
            pdf_filename=filename,
        )
        result.sent = True
    except Exception as exc:
        log.exception(
            "monthly_report_send_failed", tenant_id=tenant_id, error=str(exc)
        )
        result.error = f"send: {exc!s}"
    return result


def run_monthly(
    *,
    now: datetime | None = None,
    year: int | None = None,
    month: int | None = None,
) -> MonthlyRunResult:
    """Cron entrypoint. Sends the previous-month report to every active tenant.

    Parameters:
        now:   wall-clock override for tests; defaults to current UTC.
        year/month: explicit period override. When provided, BOTH must be set
            and `now` is ignored for period selection. Useful for back-fills
            via a manual cron call.
    """
    if (year is None) != (month is None):
        raise ValueError("year and month must be provided together")

    if year is None or month is None:
        current = now or datetime.now(UTC)
        target_year, target_month = (
            monthly_report_service.resolve_previous_complete_month(current)
        )
    else:
        target_year, target_month = year, month

    active = tenants.list_active_for_cron()
    log.info(
        "monthly_report_run_start",
        year=target_year,
        month=target_month,
        tenants=len(active),
    )

    per_tenant: list[TenantMonthlyResult] = []
    total_sent = 0
    for row in active:
        tres = _process_tenant(row, year=target_year, month=target_month)
        per_tenant.append(tres)
        if tres.sent:
            total_sent += 1

    log.info(
        "monthly_report_run_complete",
        year=target_year,
        month=target_month,
        tenants_scanned=len(active),
        total_sent=total_sent,
    )

    return MonthlyRunResult(
        year=target_year,
        month=target_month,
        tenants_scanned=len(active),
        total_sent=total_sent,
        by_tenant=per_tenant,
    )
