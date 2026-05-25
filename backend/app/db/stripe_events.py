from typing import Any

from app.services.supabase_client import get_supabase_admin


def claim(event_id: str, event_type: str, payload: dict[str, Any]) -> bool:
    """Record a Stripe event as seen. Returns False if it was already recorded.

    Stripe re-delivers events on any non-2xx response, so handlers run the risk
    of double-processing. We persist the event_id as the natural PK and let the
    UNIQUE constraint be our lock: the first writer wins, every retry sees the
    insert fail and short-circuits.

    Returns:
        True  — first time we see this event; caller should process it.
        False — already in the table; caller must NOT reprocess.
    """
    client = get_supabase_admin()
    try:
        client.table("stripe_webhook_events").insert(
            {
                "event_id": event_id,
                "type": event_type,
                "payload": payload,
            }
        ).execute()
    except Exception as exc:
        # Postgres unique_violation is SQLSTATE 23505; PostgREST surfaces it
        # with a message containing "duplicate key". Match by message so we
        # don't depend on the exact APIError shape across supabase-py versions.
        msg = str(exc)
        if "23505" in msg or "duplicate key" in msg.lower():
            return False
        raise
    return True
