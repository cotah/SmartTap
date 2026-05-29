"""Google Business Profile client (S5 Feature 3).

Build-to-activate: `is_configured()` gates everything and the read/publish
methods no-op without credentials, so dev/CI run without a Google app. The
Business Profile API is access-gated by Google (quota 0 until approved); this
client is ready to switch on the moment the env vars + a tenant connection
exist — no code change.

Responsibilities:
    - build_consent_url / exchange_code: per-tenant OAuth (business.manage)
    - list_new_reviews: pull a location's reviews (normalised)
    - publish_reply: post the owner-approved reply

The exact v4 endpoints/shapes are Google's; calls are written defensively so a
schema drift degrades to "no reviews" rather than crashing the cron.
"""

from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 — URL, not a secret
_SCOPE = "https://www.googleapis.com/auth/business.manage"
_MYBUSINESS_BASE = "https://mybusiness.googleapis.com/v4"
_HTTP_TIMEOUT = 15.0

# Google returns star ratings as an enum, not an integer.
_STAR_MAP = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


def is_configured() -> bool:
    s = get_settings()
    return bool(s.google_client_id and s.google_client_secret and s.google_oauth_redirect)


def build_consent_url(state: str) -> str:
    """OAuth consent URL for a tenant to grant business.manage. `state` carries
    the signed tenant reference back to the callback. access_type=offline +
    prompt=consent ensures we get a refresh token."""
    s = get_settings()
    params = {
        "client_id": s.google_client_id,
        "redirect_uri": s.google_oauth_redirect,
        "response_type": "code",
        "scope": _SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict[str, Any]:
    """Exchange an auth code for tokens. Returns the token response dict
    (contains refresh_token). Raises on HTTP failure — the callback handles it."""
    s = get_settings()
    resp = httpx.post(
        _TOKEN_URL,
        data={
            "code": code,
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "redirect_uri": s.google_oauth_redirect,
            "grant_type": "authorization_code",
        },
        timeout=_HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return dict(resp.json())


def _access_token(refresh_token: str) -> str | None:
    s = get_settings()
    resp = httpx.post(
        _TOKEN_URL,
        data={
            "refresh_token": refresh_token,
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "grant_type": "refresh_token",
        },
        timeout=_HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    return str(token) if token else None


def _normalise_review(raw: dict[str, Any]) -> dict[str, Any] | None:
    review_id = raw.get("reviewId") or raw.get("name")
    if not review_id:
        return None
    reviewer = raw.get("reviewer") or {}
    return {
        "google_review_id": str(review_id),
        "author": reviewer.get("displayName"),
        "rating": _STAR_MAP.get(str(raw.get("starRating", "")).upper()),
        "comment": raw.get("comment"),
        "created_at_google": raw.get("createTime"),
    }


def list_new_reviews(connection: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch reviews for the connected location, normalised. Returns [] when
    not configured or the connection is incomplete — the cron treats that as
    "nothing to do" so an unconfigured env is a safe no-op."""
    if not is_configured():
        return []
    account_id = connection.get("account_id")
    location_id = connection.get("location_id")
    refresh_token = connection.get("refresh_token")
    if not (account_id and location_id and refresh_token):
        return []

    try:
        token = _access_token(str(refresh_token))
        if not token:
            return []
        url = f"{_MYBUSINESS_BASE}/accounts/{account_id}/locations/{location_id}/reviews"
        resp = httpx.get(
            url, headers={"Authorization": f"Bearer {token}"}, timeout=_HTTP_TIMEOUT
        )
        resp.raise_for_status()
        raw_reviews = resp.json().get("reviews", []) or []
    except Exception as exc:
        log.warning("google_list_reviews_failed", error=str(exc))
        return []

    out: list[dict[str, Any]] = []
    for raw in raw_reviews:
        norm = _normalise_review(raw)
        if norm is not None:
            out.append(norm)
    return out


def publish_reply(connection: dict[str, Any], google_review_id: str, text: str) -> bool:
    """Post a reply to a review. Returns True on success. No-op (returns False)
    when not configured — the caller keeps the review out of 'published' so it
    can be retried once the API is live."""
    if not is_configured():
        log.info("google_publish_skip", reason="not_configured")
        return False
    account_id = connection.get("account_id")
    location_id = connection.get("location_id")
    refresh_token = connection.get("refresh_token")
    if not (account_id and location_id and refresh_token):
        return False

    token = _access_token(str(refresh_token))
    if not token:
        return False
    url = (
        f"{_MYBUSINESS_BASE}/accounts/{account_id}/locations/{location_id}"
        f"/reviews/{google_review_id}/reply"
    )
    resp = httpx.put(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"comment": text},
        timeout=_HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    log.info("google_reply_published", review_suffix=google_review_id[-8:])
    return True
