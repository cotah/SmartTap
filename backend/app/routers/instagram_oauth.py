"""Instagram (Meta) OAuth for the DM assistant.

Mirrors google_oauth.py exactly:
    1. GET /instagram/connect (authenticated) -> returns the consent URL with a
       signed `state` carrying the tenant. The dashboard navigates the browser
       there. JSON rather than 302 because the browser's top-level navigation
       wouldn't carry the Supabase bearer token.
    2. GET /instagram/callback (public — Meta calls it) -> verify state,
       exchange the code for a long-lived token, resolve the Page + IG account,
       store the connection, redirect back to the dashboard settings page.

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
from app.db import meta_connections
from app.dependencies import get_current_tenant_id
from app.services import meta_client

router = APIRouter(tags=["instagram"])
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


@router.get("/instagram/connect")
def instagram_connect(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> dict[str, str]:
    """Return the Meta consent URL for this tenant to authorise Instagram DMs."""
    if not meta_client.is_configured():
        raise HTTPException(status_code=503, detail="Instagram integration not configured")
    url = meta_client.build_consent_url(_sign_state(tenant_id))
    return {"url": url}


@router.get("/instagram/status")
def instagram_status(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> dict[str, Any]:
    """Whether this tenant has a live Instagram connection, for the dashboard
    to render the connected/disconnected state. Never returns the page token —
    only the safe metadata the UI needs."""
    conn = meta_connections.get_by_tenant(tenant_id)
    if conn is None:
        return {"connected": False}
    return {
        "connected": True,
        "instagram_business_account_id": conn.get("instagram_business_account_id"),
        "facebook_page_id": conn.get("facebook_page_id"),
        "connected_at": conn.get("connected_at"),
    }


@router.post("/instagram/disconnect")
def instagram_disconnect(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> dict[str, bool]:
    """Remove this tenant's Instagram connection. Idempotent — disconnecting
    when not connected still returns ok so the UI can treat it as success."""
    meta_connections.delete(tenant_id)
    log.info("instagram_disconnected", tenant_id=tenant_id)
    return {"ok": True}


@router.get("/instagram/callback")
def instagram_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """OAuth redirect target. Verifies state, exchanges the code, resolves the
    Page + IG account, stores the connection, then sends the owner back to the
    dashboard. Always redirects (never raises a raw error to the browser)."""
    base = get_settings().site_url.rstrip("/")
    dest_ok = f"{base}/dashboard/settings?instagram_connected=1"
    dest_err = f"{base}/dashboard/settings?instagram_connected=0"

    if error or not code or not state:
        log.warning("instagram_callback_missing_params", error=error)
        return RedirectResponse(url=dest_err, status_code=302)

    tenant_id = _verify_state(state)
    if tenant_id is None:
        log.warning("instagram_callback_bad_state")
        return RedirectResponse(url=dest_err, status_code=302)

    try:
        user_token = meta_client.exchange_code(code)
        if not user_token:
            raise ValueError("no long-lived token from code exchange")
        page = meta_client.resolve_page_connection(user_token)
        if page is None:
            raise ValueError("no Facebook Page with a linked Instagram business account")
        meta_connections.upsert(
            tenant_id=tenant_id,
            instagram_business_account_id=page["instagram_business_account_id"],
            facebook_page_id=page["facebook_page_id"],
            page_access_token=page["page_access_token"],
        )
        # Without this subscription Meta never delivers DMs to our webhook.
        # Treat a failed subscribe as a failed connect — reconnecting reruns
        # the whole flow and both upsert and subscribe are idempotent.
        if not meta_client.subscribe_page_to_app(
            page_id=page["facebook_page_id"],
            page_access_token=page["page_access_token"],
        ):
            raise ValueError("page webhook subscription failed")
    except Exception as exc:
        log.exception("instagram_callback_exchange_failed", error=str(exc))
        return RedirectResponse(url=dest_err, status_code=302)

    log.info("instagram_connected", tenant_id=tenant_id)
    return RedirectResponse(url=dest_ok, status_code=302)
