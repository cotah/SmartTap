from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def get_by_tag_uuid(tag_uuid: str) -> Row | None:
    client = get_supabase_admin()
    res = client.table("nfc_tags").select("*").eq("tag_uuid", tag_uuid).limit(1).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_id(tag_id: str) -> Row | None:
    client = get_supabase_admin()
    res = client.table("nfc_tags").select("*").eq("id", tag_id).limit(1).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_ids(tag_ids: list[str]) -> list[Row]:
    """Batch lookup used by the monthly report when resolving the top tag's
    human-friendly label. Returns whatever rows exist; missing ids are
    silently dropped (a deleted tag should not crash a report)."""
    if not tag_ids:
        return []
    client = get_supabase_admin()
    res = (
        client.table("nfc_tags")
        .select("id,format,color,location_name")
        .in_("id", tag_ids)
        .execute()
    )
    return cast(list[Row], res.data or [])
