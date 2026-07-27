"""Tests for the Instagram OAuth router + page webhook subscription.

Mirrors test_google_oauth.py: state helpers indirectly, public callback
end-to-end via TestClient. Adds coverage for subscribe_page_to_app — the
callback must subscribe the Page to the app (webhook field `messages`)
right after storing the connection, or inbound DMs never fire the webhook.
"""

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import _configure_logging, app
from app.routers import instagram_oauth
from app.services import meta_client

client = TestClient(app)


@pytest.fixture(autouse=True)
def _secret(monkeypatch: pytest.MonkeyPatch) -> None:
    class S:
        supabase_jwt_secret = "test-secret"
        site_url = "https://smarttap.test"

    monkeypatch.setattr(instagram_oauth, "get_settings", lambda: S())


def _page() -> dict[str, str]:
    return {
        "facebook_page_id": "page-1",
        "instagram_business_account_id": "ig-1",
        "page_access_token": "PAT-123",
    }


def test_callback_success_subscribes_page(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    subscribed: dict[str, Any] = {}
    monkeypatch.setattr(instagram_oauth.meta_client, "exchange_code", lambda code: "UT-1")
    monkeypatch.setattr(
        instagram_oauth.meta_client, "resolve_page_connection", lambda t: _page()
    )
    monkeypatch.setattr(
        instagram_oauth.meta_connections, "upsert", lambda **kw: captured.update(kw)
    )
    monkeypatch.setattr(
        instagram_oauth.meta_client,
        "subscribe_page_to_app",
        lambda **kw: subscribed.update(kw) or True,
    )

    state = instagram_oauth._sign_state("tenant-123")
    resp = client.get(
        "/v1/instagram/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert "instagram_connected=1" in resp.headers["location"]
    assert captured["tenant_id"] == "tenant-123"
    # The Page must be subscribed with the token that was just stored.
    assert subscribed == {"page_id": "page-1", "page_access_token": "PAT-123"}


def test_callback_subscribe_failure_redirects_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(instagram_oauth.meta_client, "exchange_code", lambda code: "UT-1")
    monkeypatch.setattr(
        instagram_oauth.meta_client, "resolve_page_connection", lambda t: _page()
    )
    monkeypatch.setattr(instagram_oauth.meta_connections, "upsert", lambda **kw: None)
    monkeypatch.setattr(
        instagram_oauth.meta_client, "subscribe_page_to_app", lambda **kw: False
    )

    state = instagram_oauth._sign_state("tenant-123")
    resp = client.get(
        "/v1/instagram/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert "instagram_connected=0" in resp.headers["location"]


def test_subscribe_page_to_app_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    class Resp:
        def raise_for_status(self) -> None: ...
        def json(self) -> dict[str, Any]:
            return {"success": True}

    def fake_post(url: str, **kw: Any) -> Resp:
        calls["url"] = url
        calls["kw"] = kw
        return Resp()

    monkeypatch.setattr(meta_client.httpx, "post", fake_post)

    ok = meta_client.subscribe_page_to_app(page_id="page-1", page_access_token="PAT-123")

    assert ok is True
    assert "/page-1/subscribed_apps" in calls["url"]
    # Secrets travel in the POST body, never in the URL (log hygiene).
    assert "PAT-123" not in calls["url"]
    assert calls["kw"]["data"]["access_token"] == "PAT-123"
    assert calls["kw"]["data"]["subscribed_fields"] == "messages"


def test_subscribe_page_to_app_failure_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(url: str, **kw: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(meta_client.httpx, "post", fake_post)
    assert meta_client.subscribe_page_to_app(page_id="p", page_access_token="t") is False


def test_httpx_request_urls_not_logged_at_info() -> None:
    """httpx logs full request URLs (with client_secret / access_token query
    params) at INFO — our logging config must silence that channel.

    Under pytest `basicConfig` is a no-op (root already has handlers), so we
    recreate the prod state explicitly: root at INFO, no per-logger overrides.
    """
    root = logging.getLogger()
    prev_root = root.level
    try:
        logging.getLogger("httpx").setLevel(logging.NOTSET)
        logging.getLogger("httpcore").setLevel(logging.NOTSET)
        root.setLevel(logging.INFO)

        _configure_logging("INFO")

        assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
        assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING
    finally:
        root.setLevel(prev_root)
