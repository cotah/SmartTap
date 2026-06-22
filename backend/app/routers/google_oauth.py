"""Google Business Profile OAuth (S5 Feature 3, Phase A).

Connect flow:
    1. GET /google/connect (authenticated) -> returns the consent URL with a
       signed `state` carrying the tenant. The dashboard navigates the browser
       there. We return JSON rather than 302 because the browser's top-level
       navigation wouldn't carry the Supabase bearer token.
    2. GET /google/callback (public — Google calls it) -> verify state, exchange
       the code for a refresh token, store the connection, redirect back to the
       dashboard.

`state` is HMAC-signed with the Supabase JWT secret so the callback can trust
the tenant without a session (the callback has no auth header).
"""

import hashlib
import hmac
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.db import google_connections
from app.dependencies import get_current_tenant_id
from app.services import google_client

router = APIRouter(tags=["google"])
log = structlog.get_logger(__name__)


def _sign_state(tenant_id: str) -> str:
    secret = get_settings().supabase_jwt_secret.encode("utf-8")
    sig = hmac.new(secret, tenant_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{tenant_id}.{sig}"


def _verify_state(state: str) -> str | None:
    if "." not in state:
        return None
    tenant_id, sig = state.rsplit(".", 1)
    expected = hmac.new(
        get_settings().supabase_jwt_secret.encode("utf-8"),
        tenant_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return tenant_id if hmac.compare_digest(expected, sig) else None


@router.get("/google/connect")
def google_connect(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> dict[str, str]:
    """Return the Google consent URL for this tenant to authorise review access."""
    if not google_client.is_configured():
        raise HTTPException(status_code=503, detail="Google integration not configured")
    url = google_client.build_consent_url(_sign_state(tenant_id))
    return {"url": url}


@router.get("/google/status")
def google_status(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> dict[str, Any]:
    """Whether this tenant has a live Google Business connection, for the
    dashboard to render the connected/disconnected state. Never returns the
    refresh token — only the safe metadata the UI needs."""
    conn = google_connections.get_by_tenant(tenant_id)
    if conn is None:
        return {"connected": False}
    return {
        "connected": True,
        "account_name": conn.get("account_name"),
        "account_id": conn.get("account_id"),
        "location_id": conn.get("location_id"),
        "connected_at": conn.get("connected_at"),
    }


@router.post("/google/disconnect")
def google_disconnect(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> dict[str, bool]:
    """Remove this tenant's Google Business connection. Idempotent — disconnecting
    when not connected still returns ok so the UI can treat it as success."""
    google_connections.delete(tenant_id)
    log.info("google_disconnected", tenant_id=tenant_id)
    return {"ok": True}


@router.get("/google/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """OAuth redirect target. Verifies state, exchanges the code, stores the
    refresh token, then sends the owner back to the dashboard. Always redirects
    (never raises a raw error to the browser) so the UX is a clean return."""
    base = get_settings().site_url.rstrip("/")
    dest_ok = f"{base}/dashboard/reviews?connected=1"
    dest_err = f"{base}/dashboard/reviews?connected=0"

    if error or not code or not state:
        log.warning("google_callback_missing_params", error=error)
        return RedirectResponse(url=dest_err, status_code=302)

    tenant_id = _verify_state(state)
    if tenant_id is None:
        log.warning("google_callback_bad_state")
        return RedirectResponse(url=dest_err, status_code=302)

    try:
        tokens = google_client.exchange_code(code)
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise ValueError("no refresh_token in token response")
        # Resolve the account name + ids so the dashboard can show which account
        # is linked and the reviews cron has the account/location to query.
        # Best-effort: returns all-None on failure, the connection still saves.
        meta = google_client.fetch_account_and_location(str(refresh_token))
        google_connections.upsert(
            tenant_id=tenant_id,
            refresh_token=str(refresh_token),
            account_id=meta.get("account_id"),
            location_id=meta.get("location_id"),
            account_name=meta.get("account_name"),
        )
    except Exception as exc:
        log.exception("google_callback_exchange_failed", error=str(exc))
        return RedirectResponse(url=dest_err, status_code=302)

    log.info("google_connected", tenant_id=tenant_id)
    return RedirectResponse(url=dest_ok, status_code=302)
