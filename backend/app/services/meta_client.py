"""Meta Graph API client for the Instagram DM assistant.

Same configuration discipline as the other external clients: `is_configured()`
gates everything and the client no-ops cleanly without credentials so dev/CI
run without a Meta app.

Responsibilities:
    - build_consent_url / exchange_code: per-tenant Facebook Login OAuth,
      exchanged straight to a long-lived user token
    - list_page_connections: all the tenant's Facebook Pages with a linked
      Instagram business account + their page access tokens
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


def list_page_connections(user_token: str) -> list[dict[str, str | None]] | None:
    """All Facebook Pages with a linked Instagram business account from
    /me/accounts, so the callback can connect directly (one page) or let the
    owner pick (several). Returns a list of {facebook_page_id, page_name,
    instagram_business_account_id, ig_username, page_access_token}, [] when
    none qualify, or None when the Graph call itself fails.
    """
    s = get_settings()
    try:
        resp = httpx.get(
            f"{_GRAPH_BASE}/{s.meta_api_version}/me/accounts",
            params={
                "fields": "id,name,access_token,instagram_business_account{id,username}",
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
        return []
    if len(qualifying) > 1:
        # Metadata only — tokens must never reach the logs.
        log.info(
            "meta_multiple_instagram_pages",
            pages=[
                {
                    "page_id": str(p["id"]),
                    "name": p.get("name"),
                    "ig_id": str(p["instagram_business_account"]["id"]),
                    "ig_username": p["instagram_business_account"].get("username"),
                }
                for p in qualifying
            ],
        )

    return [
        {
            "facebook_page_id": str(p["id"]),
            "page_name": p.get("name"),
            "instagram_business_account_id": str(p["instagram_business_account"]["id"]),
            "ig_username": p["instagram_business_account"].get("username"),
            "page_access_token": str(p["access_token"]),
        }
        for p in qualifying
    ]


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


def subscribe_page_to_app(*, page_id: str, page_access_token: str) -> bool:
    """Subscribe the Facebook Page to this app's webhook (field `messages`).
    Without this, Meta never delivers inbound DMs to /v1/webhooks/instagram.
    Returns True on success, False on any failure — the callback treats a
    failed subscribe as a failed connect (reconnecting is idempotent).

    The token goes in the POST body (`data=`), never the URL, so it can't
    leak through request logging."""
    s = get_settings()
    url = f"{_GRAPH_BASE}/{s.meta_api_version}/{page_id}/subscribed_apps"
    try:
        resp = httpx.post(
            url,
            data={
                "subscribed_fields": "messages",
                "access_token": page_access_token,
            },
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        ok = bool(resp.json().get("success"))
    except httpx.HTTPStatusError as exc:
        log.warning(
            "instagram_subscribe_failed",
            status=exc.response.status_code,
            body=exc.response.text[:500],
        )
        return False
    except Exception as exc:
        log.warning("instagram_subscribe_error", error=str(exc))
        return False
    if not ok:
        log.warning("instagram_subscribe_not_confirmed", page_suffix=page_id[-4:])
    return ok


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
