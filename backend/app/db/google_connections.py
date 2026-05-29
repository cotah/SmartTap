"""DB access for per-tenant Google Business Profile connections (S5 Feature 3).

The refresh_token is encrypted at rest with pgcrypto (audit follow-up 1). All
access goes through SECURITY DEFINER RPC functions that encrypt/decrypt inside
Postgres; the symmetric key lives only in the backend env
(GOOGLE_TOKEN_ENC_KEY) and is passed per call — never stored in the DB.

Python signatures are unchanged from the plaintext version, so callers and the
returned row shape ({tenant_id, refresh_token, account_id, location_id}) stay
the same.
"""

from typing import Any, cast

from app.config import get_settings
from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def _key() -> str | None:
    return get_settings().google_token_enc_key or None


def get_by_tenant(tenant_id: str) -> Row | None:
    key = _key()
    if not key:
        # No key configured → nothing usable (Google not wired up yet).
        return None
    client = get_supabase_admin()
    res = client.rpc(
        "google_conn_get", {"p_tenant_id": tenant_id, "p_key": key}
    ).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def upsert(
    *,
    tenant_id: str,
    refresh_token: str,
    account_id: str | None = None,
    location_id: str | None = None,
) -> Row:
    """Create or replace a tenant's connection, encrypting the refresh token.
    Raises if the encryption key isn't configured — we must never persist a
    token in plaintext."""
    key = _key()
    if not key:
        raise RuntimeError("GOOGLE_TOKEN_ENC_KEY not configured; refusing to store token")
    client = get_supabase_admin()
    client.rpc(
        "google_conn_upsert",
        {
            "p_tenant_id": tenant_id,
            "p_refresh_token": refresh_token,
            "p_account_id": account_id,
            "p_location_id": location_id,
            "p_key": key,
        },
    ).execute()
    return {"tenant_id": tenant_id, "account_id": account_id, "location_id": location_id}


def list_connected() -> list[Row]:
    """All tenant connections (decrypted) — the review-responses cron iterates
    these. Returns [] when no key is configured."""
    key = _key()
    if not key:
        return []
    client = get_supabase_admin()
    res = client.rpc("google_conn_list", {"p_key": key}).execute()
    return cast(list[Row], res.data or [])
