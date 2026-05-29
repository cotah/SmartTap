"""DB access for per-tenant Google Business Profile connections (S5 Feature 3).

Pure CRUD. The refresh token stored here is sensitive — only the service-role
key reads this table (RLS is on). Encrypting at rest is a tracked follow-up.
"""

from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def get_by_tenant(tenant_id: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("tenant_google_connections")
        .select("*")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def upsert(
    *,
    tenant_id: str,
    refresh_token: str,
    account_id: str | None = None,
    location_id: str | None = None,
) -> Row:
    """Create or replace a tenant's connection. on_conflict=tenant_id so
    re-connecting overwrites the stored token rather than erroring on the
    UNIQUE constraint."""
    client = get_supabase_admin()
    payload: Row = {
        "tenant_id": tenant_id,
        "refresh_token": refresh_token,
        "account_id": account_id,
        "location_id": location_id,
    }
    res = (
        client.table("tenant_google_connections")
        .upsert(payload, on_conflict="tenant_id")
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("google connection not upserted")
    return rows[0]


def list_connected() -> list[Row]:
    """All tenant connections — the review-responses cron iterates these."""
    client = get_supabase_admin()
    res = client.table("tenant_google_connections").select("*").execute()
    return cast(list[Row], res.data or [])
