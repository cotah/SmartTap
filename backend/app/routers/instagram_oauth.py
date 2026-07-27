"""Instagram (Meta) OAuth for the DM assistant.

Mirrors google_oauth.py:
    1. GET /instagram/connect (authenticated) -> returns the consent URL with a
       signed `state` carrying the tenant. The dashboard navigates the browser
       there. JSON rather than 302 because the browser's top-level navigation
       wouldn't carry the Supabase bearer token.
    2. GET /instagram/callback (public — Meta calls it) -> verify state,
       exchange the code for a long-lived token, list the Pages with a linked
       IG account. Exactly one → connect directly. Several → park a pending
       selection (encrypted user token, 10-min TTL) and redirect the dashboard
       to the Page Picker (?instagram_select=1).
    3. GET /instagram/pages + POST /instagram/select (authenticated) -> the
       Page Picker. Select re-resolves page tokens from the parked user token;
       tokens never round-trip through the browser or the pending jsonb.

`state` is HMAC-signed with the Supabase JWT secret so the callback can trust
the tenant without a session (the callback has no auth header).
"""

import hashlib
import hmac
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config import get_settings
from app.db import meta_connections, meta_pending
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


def _connect_page(tenant_id: str, page: dict[str, Any]) -> None:
    """Store the connection + subscribe the Page to the app webhook. Raises on
    subscribe failure — without the subscription Meta never delivers DMs, so
    a half-connected state must surface as a failed connect."""
    meta_connections.upsert(
        tenant_id=tenant_id,
        instagram_business_account_id=page["instagram_business_account_id"],
        facebook_page_id=page["facebook_page_id"],
        page_access_token=page["page_access_token"],
        page_name=page.get("page_name"),
        ig_username=page.get("ig_username"),
    )
    if not meta_client.subscribe_page_to_app(
        page_id=page["facebook_page_id"],
        page_access_token=page["page_access_token"],
    ):
        raise ValueError("page webhook subscription failed")


def _display_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip page access tokens — the pending jsonb and the dashboard only
    ever see display metadata."""
    return [
        {
            "facebook_page_id": p["facebook_page_id"],
            "page_name": p.get("page_name"),
            "instagram_business_account_id": p["instagram_business_account_id"],
            "ig_username": p.get("ig_username"),
        }
        for p in pages
    ]


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
        "page_name": conn.get("page_name"),
        "ig_username": conn.get("ig_username"),
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


@router.get("/instagram/pages")
def instagram_pages(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> dict[str, Any]:
    """The pending Page Picker candidates for this tenant (display data only).
    Empty when there's no pending selection or it expired — the UI should
    prompt the owner to reconnect."""
    pending = meta_pending.get(tenant_id)
    if pending is None:
        return {"pages": []}
    return {"pages": pending.get("pages") or []}


class SelectPageBody(BaseModel):
    facebook_page_id: str


@router.post("/instagram/select")
def instagram_select(
    body: SelectPageBody,
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> dict[str, bool]:
    """Connect the page the owner picked. Re-resolves page tokens from the
    parked user token — the browser only ever sends the page id."""
    pending = meta_pending.get(tenant_id)
    if pending is None:
        raise HTTPException(
            status_code=404,
            detail="No pending Instagram selection — reconnect Instagram to start over",
        )
    pages = meta_client.list_page_connections(pending["user_token"]) or []
    page = next(
        (p for p in pages if p["facebook_page_id"] == body.facebook_page_id), None
    )
    if page is None:
        raise HTTPException(
            status_code=400,
            detail="That page is no longer available — reconnect Instagram and try again",
        )
    try:
        _connect_page(tenant_id, page)
    except Exception as exc:
        log.exception("instagram_select_connect_failed", error=str(exc))
        raise HTTPException(
            status_code=502, detail="Could not connect the selected page"
        ) from exc
    meta_pending.delete(tenant_id)
    log.info("instagram_connected", tenant_id=tenant_id, via="page_picker")
    return {"ok": True}


@router.get("/instagram/callback")
def instagram_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """OAuth redirect target. Verifies state, exchanges the code, then either
    connects the single qualifying Page directly or parks a pending selection
    for the Page Picker. Always redirects (never raises a raw error to the
    browser)."""
    base = get_settings().site_url.rstrip("/")
    dest_ok = f"{base}/dashboard/settings?instagram_connected=1"
    dest_err = f"{base}/dashboard/settings?instagram_connected=0"
    dest_select = f"{base}/dashboard/settings?instagram_select=1"

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
        pages = meta_client.list_page_connections(user_token)
        if not pages:
            raise ValueError("no Facebook Page with a linked Instagram business account")
        if len(pages) > 1:
            # Owner manages several IG-linked pages — let them pick in the
            # dashboard. The user token is parked encrypted with a short TTL.
            meta_pending.upsert(
                tenant_id=tenant_id,
                user_token=user_token,
                pages=_display_pages(pages),
            )
            log.info("instagram_pending_selection", tenant_id=tenant_id, count=len(pages))
            return RedirectResponse(url=dest_select, status_code=302)
        _connect_page(tenant_id, pages[0])
    except Exception as exc:
        log.exception("instagram_callback_exchange_failed", error=str(exc))
        return RedirectResponse(url=dest_err, status_code=302)

    log.info("instagram_connected", tenant_id=tenant_id)
    return RedirectResponse(url=dest_ok, status_code=302)
