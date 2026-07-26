"""DB access for the Instagram DM assistant's interaction log.

Pure CRUD: the webhook service logs every handled DM / story mention here
(answered or failed), and the monthly report counts them per period.
"""

from datetime import datetime
from typing import Any, cast

from postgrest import CountMethod

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]

InteractionType = str  # dm | story_mention
Status = str  # answered | pending_approval | failed


def create(
    *,
    tenant_id: str,
    interaction_type: InteractionType,
    external_sender_id: str,
    incoming_text: str | None,
    reply_text: str | None,
    status: Status = "answered",
) -> Row:
    client = get_supabase_admin()
    payload: Row = {
        "tenant_id": tenant_id,
        "interaction_type": interaction_type,
        "external_sender_id": external_sender_id,
        "incoming_text": incoming_text,
        "reply_text": reply_text,
        "status": status,
    }
    res = client.table("instagram_interactions").insert(payload).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("instagram interaction not created")
    return rows[0]


def count_in_range(
    tenant_id: str,
    *,
    start: datetime,
    end: datetime,
    interaction_type: InteractionType | None = None,
    status: Status | None = None,
) -> int:
    """Interactions for a tenant in [start, end). The monthly report uses this
    to count DMs and story mentions answered in the period."""
    client = get_supabase_admin()
    query = (
        client.table("instagram_interactions")
        .select("id", count=CountMethod.exact)
        .eq("tenant_id", tenant_id)
        .gte("created_at", start.isoformat())
        .lt("created_at", end.isoformat())
    )
    if interaction_type is not None:
        query = query.eq("interaction_type", interaction_type)
    if status is not None:
        query = query.eq("status", status)
    res = query.execute()
    return int(res.count or 0)
