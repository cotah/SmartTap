from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def create(
    *,
    tag_id: str,
    tenant_id: str,
    customer_id: str | None,
    device_type: str,
    interaction_type: str,
    user_agent: str | None,
    ip_hash: str | None,
    action_taken: str | None = None,
) -> Row:
    client = get_supabase_admin()
    payload: dict[str, Any] = {
        "tag_id": tag_id,
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "device_type": device_type,
        "interaction_type": interaction_type,
        "user_agent": user_agent,
        "ip_hash": ip_hash,
        "action_taken": action_taken,
    }
    res = client.table("taps").insert(payload).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("tap not created")
    return rows[0]


def update_action(tap_id: str, action_taken: str) -> Row:
    client = get_supabase_admin()
    res = (
        client.table("taps")
        .update({"action_taken": action_taken})
        .eq("id", tap_id)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError(f"tap {tap_id} not updated")
    return rows[0]
