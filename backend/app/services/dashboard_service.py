from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from postgrest import CountMethod

from app.services.supabase_client import get_supabase_admin


@dataclass(frozen=True)
class OverviewMetrics:
    customers_total: int
    taps_week: int
    reviews_month: int
    customers_at_risk: int
    active_stamps_total: int


AT_RISK_DAYS = 30


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
    )
