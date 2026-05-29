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
from typing import Annotated

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
        google_connections.upsert(tenant_id=tenant_id, refresh_token=str(refresh_token))
    except Exception as exc:
        log.exception("google_callback_exchange_failed", error=str(exc))
        return RedirectResponse(url=dest_err, status_code=302)

    log.info("google_connected", tenant_id=tenant_id)
    return RedirectResponse(url=dest_ok, status_code=302)
