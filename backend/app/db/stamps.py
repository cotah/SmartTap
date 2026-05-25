from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


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
