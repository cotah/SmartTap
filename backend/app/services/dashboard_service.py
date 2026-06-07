from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from postgrest import CountMethod

from app.db import taps
from app.services.supabase_client import get_supabase_admin


@dataclass(frozen=True)
class OverviewMetrics:
    customers_total: int
    taps_week: int
    reviews_month: int
    customers_at_risk: int
    active_stamps_total: int
    loyalty_visits_today: int


@dataclass(frozen=True)
class TapDayPoint:
    """One day of activity, keyed by its Dublin calendar date (YYYY-MM-DD)."""

    date: str
    stamps: int
    reviews: int


AT_RISK_DAYS = 30

# "Today" and the daily buckets are anchored in Dublin local time so the owner
# sees their own day, not a UTC day that flips at 00:00/01:00 local. Same TZ the
# monthly report uses for its weekday/hour insights.
DUBLIN_TZ = ZoneInfo("Europe/Dublin")
TIMESERIES_MAX_DAYS = 90


def _count(table: str, filters: list[tuple[str, str, Any]]) -> int:
    client = get_supabase_admin()
    query = client.table(table).select("id", count=CountMethod.exact)
    for column, op, value in filters:
        if op == "eq":
            query = query.eq(column, value)
        elif op == "gte":
            query = query.gte(column, value)
        elif op == "lt":
            query = query.lt(column, value)
        elif op == "eq_action":
            query = query.eq(column, value)
    res = query.limit(1).execute()
    return res.count or 0


def overview(tenant_id: str) -> OverviewMetrics:
    now = datetime.now(UTC)
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()
    at_risk_cutoff = (now - timedelta(days=AT_RISK_DAYS)).isoformat()

    customers_total = _count("customers", [("tenant_id", "eq", tenant_id)])
    taps_week = _count(
        "taps", [("tenant_id", "eq", tenant_id), ("created_at", "gte", week_ago)]
    )
    reviews_month = _count(
        "taps",
        [
            ("tenant_id", "eq", tenant_id),
            ("action_taken", "eq", "review_clicked"),
            ("created_at", "gte", month_ago),
        ],
    )
    customers_at_risk = _count(
        "customers",
        [("tenant_id", "eq", tenant_id), ("last_visit_at", "lt", at_risk_cutoff)],
    )

    client = get_supabase_admin()
    sum_res = (
        client.table("customers")
        .select("current_stamps")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    rows = cast(list[dict[str, Any]], sum_res.data or [])
    active_stamps_total = sum(int(r.get("current_stamps") or 0) for r in rows)

    return OverviewMetrics(
        customers_total=customers_total,
        taps_week=taps_week,
        reviews_month=reviews_month,
        customers_at_risk=customers_at_risk,
        active_stamps_total=active_stamps_total,
        loyalty_visits_today=loyalty_visits_today(tenant_id, now=now),
    )


# ---------------------------------------------------------------------------
# Dublin-anchored day math
# ---------------------------------------------------------------------------


def _today_bounds_utc(now: datetime) -> tuple[datetime, datetime]:
    """Return [start, end) in UTC for the Dublin calendar day that `now`
    falls on. Computing the next day as a calendar date (not now + 24h) keeps
    the bounds at local midnight even across a DST flip."""
    today = now.astimezone(DUBLIN_TZ).date()
    start = datetime.combine(today, time.min, tzinfo=DUBLIN_TZ)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=DUBLIN_TZ)
    return start.astimezone(UTC), end.astimezone(UTC)


def _window_bounds_utc(
    now: datetime, days: int
) -> tuple[datetime, datetime, list[str]]:
    """Return the UTC [start, end) covering the last `days` Dublin calendar
    days (inclusive of today) plus the ordered list of their ISO dates."""
    today = now.astimezone(DUBLIN_TZ).date()
    first = today - timedelta(days=days - 1)
    start = datetime.combine(first, time.min, tzinfo=DUBLIN_TZ)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=DUBLIN_TZ)
    labels = [(first + timedelta(days=i)).isoformat() for i in range(days)]
    return start.astimezone(UTC), end.astimezone(UTC), labels


def _parse_utc(value: str) -> datetime:
    """Parse a postgrest timestamptz, tolerating a trailing 'Z'."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Loyalty visits today
# ---------------------------------------------------------------------------


def loyalty_visits_today(tenant_id: str, *, now: datetime | None = None) -> int:
    """Stamp taps recorded today (Dublin). Reuses the same tap query path as
    the monthly report so the count stays consistent with other tallies."""
    now = now or datetime.now(UTC)
    start, end = _today_bounds_utc(now)
    return taps.count_in_range(
        tenant_id, start=start, end=end, action_taken="stamp_earned"
    )


# ---------------------------------------------------------------------------
# Activity timeseries
# ---------------------------------------------------------------------------


def taps_timeseries(
    tenant_id: str, *, days: int = 30, now: datetime | None = None
) -> list[TapDayPoint]:
    """Daily stamp/review tap counts over the last `days` Dublin days,
    zero-filled and ordered oldest → newest. `days` is clamped to [1, 90]."""
    days = max(1, min(days, TIMESERIES_MAX_DAYS))
    now = now or datetime.now(UTC)
    start, end, labels = _window_bounds_utc(now, days)

    buckets: dict[str, dict[str, int]] = {
        label: {"stamps": 0, "reviews": 0} for label in labels
    }
    for row in taps.list_in_range(tenant_id, start=start, end=end):
        created = row.get("created_at")
        if not created:
            continue
        day = _parse_utc(created).astimezone(DUBLIN_TZ).date().isoformat()
        bucket = buckets.get(day)
        if bucket is None:
            continue
        action = row.get("action_taken")
        if action == "stamp_earned":
            bucket["stamps"] += 1
        elif action == "review_clicked":
            bucket["reviews"] += 1

    return [
        TapDayPoint(date=label, stamps=b["stamps"], reviews=b["reviews"])
        for label, b in buckets.items()
    ]
