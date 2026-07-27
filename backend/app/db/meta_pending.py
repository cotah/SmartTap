"""DB access for pending Instagram page selections (the OAuth Page Picker).

Mirrors meta_connections.py: when the OAuth callback finds more than one
Facebook Page with a linked Instagram account, the long-lived user token is
parked here (encrypted with pgcrypto, 10-minute TTL — migration 017) until the
owner picks a page in the dashboard. The `pages` jsonb holds display data
only — page access tokens are NEVER stored; the select endpoint re-resolves
them from the decrypted user token.
"""

from typing import Any, cast

from app.config import get_settings
from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def _key() -> str | None:
    return get_settings().meta_token_enc_key or None


def upsert(*, tenant_id: str, user_token: str, pages: list[dict[str, Any]]) -> None:
    """Park the user token + candidate pages for this tenant, encrypting the
    token. Raises if the encryption key isn't configured — we must never
    persist a token in plaintext."""
    key = _key()
    if not key:
        raise RuntimeError("META_TOKEN_ENC_KEY not configured; refusing to store token")
    client = get_supabase_admin()
    client.rpc(
        "meta_pending_upsert",
        {
            "p_tenant_id": tenant_id,
            "p_user_token": user_token,
            "p_pages": pages,
            "p_key": key,
        },
    ).execute()


def get(tenant_id: str) -> Row | None:
    """This tenant's pending selection, or None when there isn't one, it has
    expired (the RPC filters on expires_at), or the key isn't configured."""
    key = _key()
    if not key:
        return None
    client = get_supabase_admin()
    res = client.rpc(
        "meta_pending_get", {"p_tenant_id": tenant_id, "p_key": key}
    ).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def delete(tenant_id: str) -> None:
    """Drop the pending selection once a page is picked (or on disconnect).
    Service-role delete — no decryption involved. Idempotent."""
    client = get_supabase_admin()
    client.table("meta_pending_connections").delete().eq("tenant_id", tenant_id).execute()
