"""DB access for per-tenant Meta (Facebook Page + Instagram) connections.

Mirrors google_connections.py: the page_access_token is encrypted at rest with
pgcrypto (migration 016). All access goes through SECURITY DEFINER RPC
functions that encrypt/decrypt inside Postgres; the symmetric key lives only
in the backend env (META_TOKEN_ENC_KEY) and is passed per call — never stored
in the DB.
"""

from typing import Any, cast

from app.config import get_settings
from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def _key() -> str | None:
    return get_settings().meta_token_enc_key or None


def get_by_tenant(tenant_id: str) -> Row | None:
    key = _key()
    if not key:
        # No key configured → nothing usable (Instagram not wired up yet).
        return None
    client = get_supabase_admin()
    res = client.rpc(
        "meta_conn_get", {"p_tenant_id": tenant_id, "p_key": key}
    ).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_ig_account(ig_account_id: str) -> Row | None:
    """The webhook's tenant lookup — entry[].id in a Meta Instagram webhook is
    the IG business account id. Returns None when no tenant is connected to
    that account (or the key isn't configured)."""
    key = _key()
    if not key:
        return None
    client = get_supabase_admin()
    res = client.rpc(
        "meta_conn_get_by_ig", {"p_ig_account_id": ig_account_id, "p_key": key}
    ).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def upsert(
    *,
    tenant_id: str,
    instagram_business_account_id: str,
    facebook_page_id: str,
    page_access_token: str,
    page_name: str | None = None,
    ig_username: str | None = None,
) -> Row:
    """Create or replace a tenant's connection, encrypting the page token.
    Raises if the encryption key isn't configured — we must never persist a
    token in plaintext. page_name/ig_username are display-only (migration
    017) so the dashboard can show WHICH account is connected."""
    key = _key()
    if not key:
        raise RuntimeError("META_TOKEN_ENC_KEY not configured; refusing to store token")
    client = get_supabase_admin()
    client.rpc(
        "meta_conn_upsert",
        {
            "p_tenant_id": tenant_id,
            "p_ig_account_id": instagram_business_account_id,
            "p_facebook_page_id": facebook_page_id,
            "p_page_access_token": page_access_token,
            "p_key": key,
            "p_page_name": page_name,
            "p_ig_username": ig_username,
        },
    ).execute()
    return {
        "tenant_id": tenant_id,
        "instagram_business_account_id": instagram_business_account_id,
        "facebook_page_id": facebook_page_id,
    }


def delete(tenant_id: str) -> None:
    """Remove a tenant's Meta connection (the dashboard 'Disconnect' action).
    Service-role delete — no decryption involved, so it doesn't go through the
    pgcrypto RPCs. Idempotent: deleting a non-existent row is a no-op."""
    client = get_supabase_admin()
    client.table("tenant_meta_connections").delete().eq("tenant_id", tenant_id).execute()
