"""Monthly report computation for SmartTap tenants.

The cron (S4-W3) generates one report per active tenant on day 1 of each
Dublin month, covering the month that just ended. The same service backs the
ad-hoc dashboard download endpoint, so identical numbers ship in both flows.

Design choices worth knowing:

    - Month boundaries are computed in **Europe/Dublin**, then converted to
      UTC for DB queries. That matches what a merchant means by "April": the
      calendar month as their till would record it, including the day flip
      at midnight local time (not 01:00 in summer / 00:00 in winter).
    - Stats requiring GROUP BY (top hour, top day, top tag) are computed in
      Python by pulling the raw tap rows in the period. PostgREST has no
      native GROUP BY and the volume per tenant per month is tiny (a few
      thousand rows at most), so this is the simplest correct path.
    - We never raise on missing data — an empty month should still produce a
      report so the merchant sees the goose egg and acts on it.
    - Previous-period stats are computed alongside the current period so the
      PDF can show deltas without a round-trip back to the service.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import structlog

from app.db import campaigns, customers, nfc_tags, rewards, stamps, taps, tenants
from app.errors import NotFoundError

log = structlog.get_logger(__name__)


DUBLIN_TZ = ZoneInfo("Europe/Dublin")

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass(frozen=True)
class PeriodStats:
    """Snapshot of the four headline KPIs plus reviews for a single period.

    Frozen so callers can hold references safely while building deltas;
    avoids accidental mutation when the same object is used as the
    'previous' bucket in a different render.
    """

    new_customers: int = 0
    total_taps: int = 0
    stamps_awarded: int = 0
    rewards_redeemed: int = 0
    reviews_clicked: int = 0


@dataclass(frozen=True)
class CampaignSummary:
    name: str
    type: str
    status: str
    multiplier: int
    days_active_in_period: int  # how many DAYS of the period the campaign was live


@dataclass(frozen=True)
class TagSummary:
    """Human-friendly identifier for the busiest NFC tag in the period."""

    label: str  # e.g. "Counter Stand · Black" or "Front desk"
    taps: int


@dataclass(frozen=True)
class MonthlyReport:
    tenant: dict[str, Any]
    year: int
    month: int  # 1-12
    # Period bounds in UTC; the PDF re-formats them in Dublin TZ for display.
    period_start: datetime
    period_end: datetime
    current: PeriodStats
    previous: PeriodStats
    # Insights — all optional because empty months are common
    best_weekday: tuple[str, int] | None = None  # (name, taps on that weekday)
    peak_hour: tuple[int, int] | None = None  # (0-23 local hour, taps)
    top_tag: TagSummary | None = None
    campaigns: list[CampaignSummary] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Period math
# ---------------------------------------------------------------------------


def _month_bounds_utc(year: int, month: int) -> tuple[datetime, datetime]:
    """Return [start, end) in UTC for the given Dublin calendar month.

    Example: May 2026 in Dublin runs 2026-05-01 00:00 IST to 2026-06-01 00:00
    IST. IST is UTC+1, so the UTC window is 2026-04-30 23:00Z to 2026-05-31
    23:00Z. The DB stores timestamps in UTC; converting once here keeps the
    rest of the code timezone-blind.
    """
    if not (1 <= month <= 12):
        raise ValueError(f"month out of range: {month}")
    start_local = datetime.combine(date(year, month, 1), time.min, tzinfo=DUBLIN_TZ)
    if month == 12:
        end_local = datetime.combine(date(year + 1, 1, 1), time.min, tzinfo=DUBLIN_TZ)
    else:
        end_local = datetime.combine(date(year, month + 1, 1), time.min, tzinfo=DUBLIN_TZ)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def resolve_previous_complete_month(now: datetime | None = None) -> tuple[int, int]:
    """The (year, month) that JUST ended in Dublin. Cron entry point uses this
    so a run on 1 May reports April. Tests inject `now` for determinism."""
    current = now or datetime.now(UTC)
    local = current.astimezone(DUBLIN_TZ)
    return _previous_month(local.year, local.month)


# ---------------------------------------------------------------------------
# Stat computation
# ---------------------------------------------------------------------------


def _period_stats(
    tenant_id: str, *, start: datetime, end: datetime
) -> PeriodStats:
    """Five lightweight count queries — each hits its own table."""
    return PeriodStats(
        new_customers=customers.count_created_in_range(tenant_id, start=start, end=end),
        total_taps=taps.count_in_range(tenant_id, start=start, end=end),
        stamps_awarded=stamps.count_in_range(tenant_id, start=start, end=end),
        rewards_redeemed=rewards.count_redeemed_in_range(tenant_id, start=start, end=end),
        reviews_clicked=taps.count_in_range(
            tenant_id, start=start, end=end, action_taken="review_clicked"
        ),
    )


def _insights(
    tenant_id: str, *, start: datetime, end: datetime
) -> tuple[tuple[str, int] | None, tuple[int, int] | None, TagSummary | None]:
    """Computes (best_weekday, peak_hour, top_tag) from a single tap fetch.

    Splitting into 3 separate queries was tempting for readability but each
    would re-scan the same rows. One fetch + three Counters is cheaper and
    keeps the operation atomic — all 3 insights see the same data even if
    new taps arrive mid-computation.
    """
    rows = taps.list_in_range(tenant_id, start=start, end=end)
    if not rows:
        return None, None, None

    weekday_counter: Counter[int] = Counter()
    hour_counter: Counter[int] = Counter()
    tag_counter: Counter[str] = Counter()

    for row in rows:
        ts_raw = row.get("created_at")
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except ValueError:
                continue
        elif isinstance(ts_raw, datetime):
            ts = ts_raw
        else:
            continue
        # Convert UTC -> Dublin so "peak hour" matches what the merchant sees
        # on their till; otherwise a 16:00 IST rush would show up as 15.
        local_ts = ts.astimezone(DUBLIN_TZ)
        weekday_counter[local_ts.weekday()] += 1
        hour_counter[local_ts.hour] += 1

        tag_id = row.get("tag_id")
        if isinstance(tag_id, str):
            tag_counter[tag_id] += 1

    best_weekday: tuple[str, int] | None = None
    if weekday_counter:
        wd, count = weekday_counter.most_common(1)[0]
        best_weekday = (WEEKDAY_NAMES[wd], count)

    peak_hour: tuple[int, int] | None = None
    if hour_counter:
        peak_hour = hour_counter.most_common(1)[0]

    top_tag: TagSummary | None = None
    if tag_counter:
        top_id, top_count = tag_counter.most_common(1)[0]
        # Resolve one row to get a friendly label. If the tag was deleted in
        # the meantime, fall back to the id so we never blank-out the line.
        rows_meta = nfc_tags.get_by_ids([top_id])
        label = _format_tag_label(rows_meta[0]) if rows_meta else f"Tag {top_id[:8]}"
        top_tag = TagSummary(label=label, taps=top_count)

    return best_weekday, peak_hour, top_tag


def _format_tag_label(row: dict[str, Any]) -> str:
    """Build a human-readable identifier from the tag's metadata. Prefers
    `location_name` (set by the merchant) over the descriptive fallback."""
    name = (row.get("location_name") or "").strip()
    if name:
        return name
    fmt = (row.get("format") or "Tag").replace("_", " ").title()
    color = (row.get("color") or "").strip()
    if color:
        return f"{fmt} · {color.title()}"
    return fmt


def _campaigns_in_period(
    tenant_id: str, *, start: datetime, end: datetime
) -> list[CampaignSummary]:
    """Campaigns that overlapped the period, with the per-period overlap in
    full days (rounded down). A campaign active 28-29 April → 1-3 May reports
    3 days in the May report, 2 in the April one."""
    summaries: list[CampaignSummary] = []
    for row in campaigns.list_overlapping_range(tenant_id, start=start, end=end):
        cstart = _parse_iso(row.get("starts_at")) or start
        cend = _parse_iso(row.get("ends_at")) or end
        overlap_start = max(cstart, start)
        overlap_end = min(cend, end)
        days = max(0, (overlap_end - overlap_start).days)
        config = row.get("config") or {}
        try:
            multiplier = int(config.get("multiplier", 1)) if isinstance(config, dict) else 1
        except (TypeError, ValueError):
            multiplier = 1
        summaries.append(
            CampaignSummary(
                name=str(row.get("name") or "Campaign"),
                type=str(row.get("type") or "unknown"),
                status=str(row.get("status") or "unknown"),
                multiplier=multiplier,
                days_active_in_period=days,
            )
        )
    return summaries


def _parse_iso(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute(
    *,
    tenant_id: str,
    year: int,
    month: int,
) -> MonthlyReport:
    """Build the full report for one tenant + one month.

    Raises NotFoundError if the tenant doesn't exist — the cron skips and
    moves on, the dashboard route turns it into a 404.
    """
    tenant = tenants.get_by_id(tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": tenant_id})

    start, end = _month_bounds_utc(year, month)
    prev_year, prev_month = _previous_month(year, month)
    prev_start, prev_end = _month_bounds_utc(prev_year, prev_month)

    current = _period_stats(tenant_id, start=start, end=end)
    previous = _period_stats(tenant_id, start=prev_start, end=prev_end)
    best_weekday, peak_hour, top_tag = _insights(tenant_id, start=start, end=end)
    campaign_summaries = _campaigns_in_period(tenant_id, start=start, end=end)

    log.info(
        "monthly_report_computed",
        tenant_id=tenant_id,
        year=year,
        month=month,
        total_taps=current.total_taps,
    )

    return MonthlyReport(
        tenant=tenant,
        year=year,
        month=month,
        period_start=start,
        period_end=end,
        current=current,
        previous=previous,
        best_weekday=best_weekday,
        peak_hour=peak_hour,
        top_tag=top_tag,
        campaigns=campaign_summaries,
    )


# Months-from-zero deltas would mean a division by zero. Caller passes the
# tuple straight from PeriodStats so this helper keeps the math in one place.
def delta_pct(current_value: int, previous_value: int) -> float | None:
    """% change vs previous period. Returns None when previous was zero
    (can't compute a meaningful percentage); the PDF renders that as a dash."""
    if previous_value <= 0:
        return None
    return ((current_value - previous_value) / previous_value) * 100.0
