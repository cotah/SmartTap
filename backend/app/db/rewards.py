from datetime import UTC, datetime
from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def get_by_id(reward_id: str) -> Row | None:
    client = get_supabase_admin()
    res = client.table("rewards").select("*").eq("id", reward_id).limit(1).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_active_for_customer(customer_id: str) -> Row | None:
    """Returns the most recent unredeemed, unexpired reward for a customer."""
    now_iso = datetime.now(UTC).isoformat()
    client = get_supabase_admin()
    res = (
        client.table("rewards")
        .select("*")
        .eq("customer_id", customer_id)
        .is_("redeemed_at", "null")
        .gt("expires_at", now_iso)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_validation_code(tenant_id: str, validation_code: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("rewards")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("validation_code", validation_code)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def create(
    *,
    customer_id: str,
    tenant_id: str,
    stamps_used: int,
    description: str,
    validation_code: str,
    expires_at: str,
) -> Row:
    client = get_supabase_admin()
    payload: dict[str, Any] = {
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "stamps_used": stamps_used,
        "description": description,
        "validation_code": validation_code,
        "expires_at": expires_at,
    }
    res = client.table("rewards").insert(payload).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("reward not created")
    return rows[0]


def redeem(reward_id: str, redeemed_by_user: str | None) -> Row:
    client = get_supabase_admin()
    res = (
        client.table("rewards")
        .update(
            {
                "redeemed_at": datetime.now(UTC).isoformat(),
                "redeemed_by_user": redeemed_by_user,
            }
        )
        .eq("id", reward_id)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError(f"reward {reward_id} not redeemed")
    return rows[0]
