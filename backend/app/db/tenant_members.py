from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def get_by_pair(tenant_id: str, user_id: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("tenant_members")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_owner_user_id(tenant_id: str) -> str | None:
    """First user with role='owner' for this tenant, or None.

    Used by email triggers to find who to notify about billing events. We
    pick the earliest-created owner so the same person consistently gets
    the notifications even after staff is added.
    """
    client = get_supabase_admin()
    res = (
        client.table("tenant_members")
        .select("user_id")
        .eq("tenant_id", tenant_id)
        .eq("role", "owner")
        .order("created_at", desc=False)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        return None
    uid = rows[0].get("user_id")
    return str(uid) if uid else None


def list_for_user(user_id: str) -> list[Row]:
    client = get_supabase_admin()
    res = (
        client.table("tenant_members")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return cast(list[Row], res.data or [])


def create(*, tenant_id: str, user_id: str, role: str = "owner") -> Row:
    client = get_supabase_admin()
    payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "role": role,
    }
    res = client.table("tenant_members").insert(payload).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("tenant_member not created")
    return rows[0]
