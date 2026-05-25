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
