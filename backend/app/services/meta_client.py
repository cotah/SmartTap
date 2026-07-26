"""Meta Graph API client for the Instagram DM assistant.

Same configuration discipline as the other external clients: `is_configured()`
gates everything and the client no-ops cleanly without credentials so dev/CI
run without a Meta app.

Responsibilities:
    - build_consent_url / exchange_code: per-tenant Facebook Login OAuth,
      exchanged straight to a long-lived user token
    - resolve_page_connection: find the tenant's Facebook Page with a linked
      Instagram business account + its page access token
    - send_dm: reply to an Instagram user via the Page's messaging endpoint
    - validate_signature / verify_token_matches: webhook authenticity (same
      X-Hub-Signature-256 scheme as the WhatsApp webhook, different app secret)

All calls are written defensively — a schema drift degrades to None rather
than crashing the webhook.
"""

import hashlib
import hmac
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

_GRAPH_BASE = "https://graph.facebook.com"
_FACEBOOK_BASE = "https://www.facebook.com"
_HTTP_TIMEOUT = 15.0

# Permissions needed to read the Page's IG account and send/receive DMs.
_SCOPES = ",".join(
    [
        "instagram_basic",
        "instagram_manage_messages",
        "pages_show_list",
        "pages_messaging",
        "pages_read_engagement",
    ]
)


def is_configured() -> bool:
    s = get_settings()
    return bool(s.meta_app_id and s.meta_app_secret and s.meta_oauth_redirect)


def build_consent_url(state: str) -> str:
    """Facebook Login consent URL for a tenant to authorise Instagram
    messaging. `state` carries the signed tenant reference back to the
    callback."""
    s = get_settings()
    params = {
        "client_id": s.meta_app_id,
        "redirect_uri": s.meta_oauth_redirect,
        "response_type": "code",
        "scope": _SCOPES,
        "state": state,
    }
    return f"{_FACEBOOK_BASE}/{s.meta_api_version}/dialog/oauth?{urlencode(params)}"


def exchange_code(code: str) -> str | None:
    """Exchange an auth code for a long-lived user access token (two steps:
    code → short-lived token → fb_exchange_token → long-lived, ~60 days).
    Returns None on any failure — the callback redirects with ?connected=0."""
    s = get_settings()
    base = f"{_GRAPH_BASE}/{s.meta_api_version}"
    try:
        resp = httpx.get(
            f"{base}/oauth/access_token",
            params={
                "client_id": s.meta_app_id,
                "client_secret": s.meta_app_secret,
                "redirect_uri": s.meta_oauth_redirect,
                "code": code,
            },
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        short_token = resp.json().get("access_token")
        if not short_token:
            return None

        resp = httpx.get(
            f"{base}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": s.meta_app_id,
                "client_secret": s.meta_app_secret,
                "fb_exchange_token": short_token,
            },
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        long_token = resp.json().get("access_token")
        return str(long_token) if long_token else None
    except Exception as exc:
        log.warning("meta_exchange_code_failed", error=str(exc))
        return None


def resolve_page_connection(user_token: str) -> dict[str, str] | None:
    """Resolve the first Facebook Page with a linked Instagram business
    account from /me/accounts. Returns {facebook_page_id,
    instagram_business_account_id, page_access_token} or None.

    We pick the FIRST qualifying page — fine for the single-location ICP;
    multi-page picking is a later enhancement and is logged so we can see
    when it matters.
    """
    s = get_settings()
    try:
        resp = httpx.get(
            f"{_GRAPH_BASE}/{s.meta_api_version}/me/accounts",
            params={
                "fields": "id,name,access_token,instagram_business_account",
                "access_token": user_token,
            },
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        pages = resp.json().get("data", []) or []
    except Exception as exc:
        log.warning("meta_resolve_pages_failed", error=str(exc))
        return None

    qualifying = [
        p
        for p in pages
        if isinstance(p, dict)
        and (p.get("instagram_business_account") or {}).get("id")
        and p.get("access_token")
        and p.get("id")
    ]
    if not qualifying:
        log.warning("meta_no_instagram_page", pages_seen=len(pages))
        return None
    if len(qualifying) > 1:
        log.info("meta_multiple_instagram_pages", count=len(qualifying))

    page = qualifying[0]
    return {
        "facebook_page_id": str(page["id"]),
        "instagram_business_account_id": str(page["instagram_business_account"]["id"]),
        "page_access_token": str(page["access_token"]),
    }


def send_dm(
    *, ig_business_account_id: str, page_access_token: str, recipient_id: str, text: str
) -> bool:
    """Send an Instagram DM reply via the messaging endpoint. Returns True on
    success, False on any failure — the webhook must never crash on a send
    error (Meta would retry and duplicate replies)."""
    s = get_settings()
    url = f"{_GRAPH_BASE}/{s.meta_api_version}/{ig_business_account_id}/messages"
    try:
        resp = httpx.post(
            url,
            params={"access_token": page_access_token},
            json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # The response body is where Meta puts the real reason (expired token,
        # messaging window closed, app not approved) — log it for debugging.
        log.warning(
            "instagram_send_dm_failed",
            status=exc.response.status_code,
            body=exc.response.text[:500],
        )
        return False
    except Exception as exc:
        log.warning("instagram_send_dm_error", error=str(exc))
        return False
    log.info("instagram_dm_sent", recipient_suffix=recipient_id[-4:])
    return True


def validate_signature(*, raw_body: bytes, signature: str | None) -> bool:
    """Verify an inbound Instagram webhook came from Meta. Same
    X-Hub-Signature-256 scheme as the WhatsApp webhook, keyed on this app's
    META_APP_SECRET. Fails closed when unconfigured."""
    s = get_settings()
    if not s.meta_app_secret or not signature:
        return False
    expected = hmac.new(
        s.meta_app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    provided = signature.removeprefix("sha256=").strip()
    return hmac.compare_digest(expected, provided)


def verify_token_matches(token: str | None) -> bool:
    """GET handshake: Meta echoes hub.verify_token; it must equal our secret.
    Constant-time compare; fails closed if the token isn't configured."""
    s = get_settings()
    if not s.meta_verify_token or not token:
        return False
    return hmac.compare_digest(s.meta_verify_token, token)


# Typing helper for callers that pass the resolved connection around.
Connection = dict[str, Any]
