"""Data access for the `campaigns` table.

Service-layer code (`campaign_service`) owns validation; this module only
talks to Postgres. Returned rows are plain dicts so callers don't depend on
postgrest-py response shapes.
"""

from datetime import datetime
from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def list_for_tenant(tenant_id: str) -> list[Row]:
    """Newest first so the dashboard shows recent activity at the top."""
    client = get_supabase_admin()
    res = (
        client.table("campaigns")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )
    return cast(list[Row], res.data or [])


def get_by_id(campaign_id: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("campaigns")
        .select("*")
        .eq("id", campaign_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def create(fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = client.table("campaigns").insert(fields).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("campaign not created")
    return rows[0]


def update(campaign_id: str, fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = (
        client.table("campaigns").update(fields).eq("id", campaign_id).execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError(f"campaign {campaign_id} not updated")
    return rows[0]


def find_active_double_stamp(tenant_id: str, at: datetime) -> Row | None:
    """The single double_stamp campaign that's live for this tenant at `at`.

    Called on every NFC tap, so this must be fast (covered by the partial
    index in migration 004). Returns None when no campaign is active — the
    most common case.

    The DB enforces that `status='active'` and `at` falls in the window. The
    service layer enforces uniqueness (only one active at a time), but we
    still apply `.limit(1)` as belt-and-suspenders in case that invariant
    ever drifts; we'd rather award too few stamps than reject taps.
    """
    client = get_supabase_admin()
    iso = at.isoformat()
    res = (
        client.table("campaigns")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("type", "double_stamp")
        .eq("status", "active")
        .lte("starts_at", iso)
        .gte("ends_at", iso)
        .order("starts_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def list_overlapping_range(
    tenant_id: str, *, start: datetime, end: datetime
) -> list[Row]:
    """Campaigns whose [starts_at, ends_at] overlaps the reporting period.

    Overlap test: campaign starts before period ends AND campaign ends after
    period starts. Includes draft/paused/ended — the monthly report shows
    EVERYTHING that ran or was scheduled, so the merchant can see what they
    intended even if they paused mid-month.
    """
    client = get_supabase_admin()
    res = (
        client.table("campaigns")
        .select("*")
        .eq("tenant_id", tenant_id)
        .lt("starts_at", end.isoformat())
        .gt("ends_at", start.isoformat())
        .order("starts_at", desc=False)
        .execute()
    )
    return cast(list[Row], res.data or [])


def has_other_active_double_stamp(
    tenant_id: str, excluding_id: str | None = None
) -> bool:
    """Check used by the service before creating/activating a campaign.
    Different from find_active_double_stamp because it doesn't require `now`
    to be inside the window — even a future-dated `active` campaign blocks,
    to keep the UX promise of "one at a time"."""
    client = get_supabase_admin()
    query = (
        client.table("campaigns")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("type", "double_stamp")
        .eq("status", "active")
    )
    if excluding_id is not None:
        query = query.neq("id", excluding_id)
    res = query.limit(1).execute()
    return bool(res.data)
