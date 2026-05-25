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
