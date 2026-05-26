"""Data access for the `customer_segments` table.

Service-layer code owns validation; this module only talks to Postgres.
Mirrors the shape of `app/db/campaigns.py` so the patterns stay uniform.
"""

from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def list_for_tenant(tenant_id: str) -> list[Row]:
    """Newest first — same ordering convention as campaigns."""
    client = get_supabase_admin()
    res = (
        client.table("customer_segments")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )
    return cast(list[Row], res.data or [])


def get_by_id(segment_id: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("customer_segments")
        .select("*")
        .eq("id", segment_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def create(fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = client.table("customer_segments").insert(fields).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("segment not created")
    return rows[0]


def update(segment_id: str, fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = (
        client.table("customer_segments")
        .update(fields)
        .eq("id", segment_id)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError(f"segment {segment_id} not updated")
    return rows[0]


def delete(segment_id: str) -> None:
    """Hard delete. Per S4-W4 scope, segments have no FKs pointing at them
    yet, so we don't need soft-delete plumbing. Future campaigns that target
    a segment will add an ON DELETE policy explicitly."""
    client = get_supabase_admin()
    client.table("customer_segments").delete().eq("id", segment_id).execute()
