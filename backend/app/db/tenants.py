from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def get_by_id(tenant_id: str) -> Row | None:
    client = get_supabase_admin()
    res = client.table("tenants").select("*").eq("id", tenant_id).limit(1).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_slug(slug: str) -> Row | None:
    client = get_supabase_admin()
    res = client.table("tenants").select("*").eq("slug", slug).limit(1).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def update(tenant_id: str, fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = client.table("tenants").update(fields).eq("id", tenant_id).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError(f"tenant {tenant_id} not updated")
    return rows[0]


def create(fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = client.table("tenants").insert(fields).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("tenant not created")
    return rows[0]
