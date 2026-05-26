from datetime import datetime
from typing import Any, cast

from postgrest import CountMethod

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def count_in_range(tenant_id: str, *, start: datetime, end: datetime) -> int:
    """Count stamps issued for a tenant in [start, end).

    Note: counts ROW count, not the sum of `multiplier`. A double-stamp
    campaign tap still inserts one stamp row; the multiplier field describes
    how it should be displayed but the issuance is one event. This matches
    how the dashboard's "stamps awarded" metric is interpreted.
    """
    client = get_supabase_admin()
    res = (
        client.table("stamps")
        .select("id", count=CountMethod.exact)
        .eq("tenant_id", tenant_id)
        .gte("created_at", start.isoformat())
        .lt("created_at", end.isoformat())
        .limit(1)
        .execute()
    )
    return res.count or 0


def last_for_customer(customer_id: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("stamps")
        .select("*")
        .eq("customer_id", customer_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def create(
    *,
    customer_id: str,
    tenant_id: str,
    tap_id: str | None,
    multiplier: int = 1,
    awarded_by: str = "auto",
    awarded_by_user: str | None = None,
) -> Row:
    client = get_supabase_admin()
    payload: dict[str, Any] = {
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "tap_id": tap_id,
        "multiplier": multiplier,
        "awarded_by": awarded_by,
        "awarded_by_user": awarded_by_user,
    }
    res = client.table("stamps").insert(payload).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("stamp not created")
    return rows[0]
