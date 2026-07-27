"""Tests for the Instagram OAuth router + page webhook subscription.

Mirrors test_google_oauth.py: state helpers indirectly, public callback
end-to-end via TestClient. Covers the Page Picker flow (migration 017): one
qualifying page connects directly; several park a pending selection and the
owner picks via GET /instagram/pages + POST /instagram/select.
"""

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_tenant_id
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


@pytest.fixture
def _auth() -> Iterator[None]:
    app.dependency_overrides[get_current_tenant_id] = lambda: "tenant-123"
    yield
    app.dependency_overrides.pop(get_current_tenant_id, None)


def _page(n: int = 1) -> dict[str, str | None]:
    return {
        "facebook_page_id": f"page-{n}",
        "page_name": f"Barber {n}",
        "instagram_business_account_id": f"ig-{n}",
        "ig_username": f"barber.{n}",
        "page_access_token": f"PAT-{n}",
    }


def _callback(state: str) -> Any:
    return client.get(
        "/v1/instagram/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )


def test_callback_single_page_connects_and_subscribes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    subscribed: dict[str, Any] = {}
    monkeypatch.setattr(instagram_oauth.meta_client, "exchange_code", lambda code: "UT-1")
    monkeypatch.setattr(
        instagram_oauth.meta_client, "list_page_connections", lambda t: [_page()]
    )
    monkeypatch.setattr(
        instagram_oauth.meta_connections, "upsert", lambda **kw: captured.update(kw)
    )
    monkeypatch.setattr(
        instagram_oauth.meta_client,
        "subscribe_page_to_app",
        lambda **kw: subscribed.update(kw) or True,
    )

    resp = _callback(instagram_oauth._sign_state("tenant-123"))

    assert resp.status_code == 302
    assert "instagram_connected=1" in resp.headers["location"]
    assert captured["tenant_id"] == "tenant-123"
    # Display metadata is stored alongside the ids (migration 017).
    assert captured["page_name"] == "Barber 1"
    assert captured["ig_username"] == "barber.1"
    # The Page must be subscribed with the token that was just stored.
    assert subscribed == {"page_id": "page-1", "page_access_token": "PAT-1"}


def test_callback_multiple_pages_parks_pending_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending: dict[str, Any] = {}
    monkeypatch.setattr(instagram_oauth.meta_client, "exchange_code", lambda code: "UT-1")
    monkeypatch.setattr(
        instagram_oauth.meta_client,
        "list_page_connections",
        lambda t: [_page(1), _page(2)],
    )
    monkeypatch.setattr(
        instagram_oauth.meta_pending, "upsert", lambda **kw: pending.update(kw)
    )

    def _fail_upsert(**kw: Any) -> None:
        raise AssertionError("must not connect before the owner picks a page")

    monkeypatch.setattr(instagram_oauth.meta_connections, "upsert", _fail_upsert)

    resp = _callback(instagram_oauth._sign_state("tenant-123"))

    assert resp.status_code == 302
    assert "instagram_select=1" in resp.headers["location"]
    assert pending["tenant_id"] == "tenant-123"
    assert pending["user_token"] == "UT-1"
    # The parked jsonb is display-only — page tokens must never land there.
    assert [p["facebook_page_id"] for p in pending["pages"]] == ["page-1", "page-2"]
    assert "page_access_token" not in str(pending["pages"])
    assert "PAT-1" not in str(pending["pages"])


def test_callback_no_pages_redirects_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(instagram_oauth.meta_client, "exchange_code", lambda code: "UT-1")
    monkeypatch.setattr(
        instagram_oauth.meta_client, "list_page_connections", lambda t: []
    )

    resp = _callback(instagram_oauth._sign_state("tenant-123"))

    assert resp.status_code == 302
    assert "instagram_connected=0" in resp.headers["location"]


def test_callback_subscribe_failure_redirects_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(instagram_oauth.meta_client, "exchange_code", lambda code: "UT-1")
    monkeypatch.setattr(
        instagram_oauth.meta_client, "list_page_connections", lambda t: [_page()]
    )
    monkeypatch.setattr(instagram_oauth.meta_connections, "upsert", lambda **kw: None)
    monkeypatch.setattr(
        instagram_oauth.meta_client, "subscribe_page_to_app", lambda **kw: False
    )

    resp = _callback(instagram_oauth._sign_state("tenant-123"))

    assert resp.status_code == 302
    assert "instagram_connected=0" in resp.headers["location"]


@pytest.mark.usefixtures("_auth")
def test_pages_lists_pending_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    display = [
        {k: v for k, v in _page(n).items() if k != "page_access_token"}
        for n in (1, 2)
    ]
    monkeypatch.setattr(
        instagram_oauth.meta_pending,
        "get",
        lambda tid: {"tenant_id": tid, "user_token": "UT-1", "pages": display},
    )

    resp = client.get("/v1/instagram/pages")

    assert resp.status_code == 200
    # Tokens (user or page) must never reach the dashboard.
    assert resp.json() == {"pages": display}


@pytest.mark.usefixtures("_auth")
def test_pages_empty_when_pending_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(instagram_oauth.meta_pending, "get", lambda tid: None)

    resp = client.get("/v1/instagram/pages")

    assert resp.status_code == 200
    assert resp.json() == {"pages": []}


@pytest.mark.usefixtures("_auth")
def test_select_connects_chosen_page(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    subscribed: dict[str, Any] = {}
    deleted: list[str] = []
    monkeypatch.setattr(
        instagram_oauth.meta_pending,
        "get",
        lambda tid: {"tenant_id": tid, "user_token": "UT-1", "pages": []},
    )
    # The select endpoint re-resolves tokens from the user token — the page
    # token never round-trips through the client or the pending jsonb.
    monkeypatch.setattr(
        instagram_oauth.meta_client,
        "list_page_connections",
        lambda t: [_page(1), _page(2)],
    )
    monkeypatch.setattr(
        instagram_oauth.meta_connections, "upsert", lambda **kw: captured.update(kw)
    )
    monkeypatch.setattr(
        instagram_oauth.meta_client,
        "subscribe_page_to_app",
        lambda **kw: subscribed.update(kw) or True,
    )
    monkeypatch.setattr(
        instagram_oauth.meta_pending, "delete", lambda tid: deleted.append(tid)
    )

    resp = client.post("/v1/instagram/select", json={"facebook_page_id": "page-2"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert captured["facebook_page_id"] == "page-2"
    assert captured["page_access_token"] == "PAT-2"
    assert captured["page_name"] == "Barber 2"
    assert captured["ig_username"] == "barber.2"
    assert subscribed["page_id"] == "page-2"
    assert deleted == ["tenant-123"]


@pytest.mark.usefixtures("_auth")
def test_select_without_pending_is_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(instagram_oauth.meta_pending, "get", lambda tid: None)

    resp = client.post("/v1/instagram/select", json={"facebook_page_id": "page-1"})

    assert resp.status_code == 404


@pytest.mark.usefixtures("_auth")
def test_select_unknown_page_is_400(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        instagram_oauth.meta_pending,
        "get",
        lambda tid: {"tenant_id": tid, "user_token": "UT-1", "pages": []},
    )
    monkeypatch.setattr(
        instagram_oauth.meta_client, "list_page_connections", lambda t: [_page(1)]
    )

    resp = client.post("/v1/instagram/select", json={"facebook_page_id": "page-9"})

    assert resp.status_code == 400


@pytest.mark.usefixtures("_auth")
def test_status_includes_display_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        instagram_oauth.meta_connections,
        "get_by_tenant",
        lambda tid: {
            "instagram_business_account_id": "ig-1",
            "facebook_page_id": "page-1",
            "connected_at": "2026-07-27T00:00:00Z",
            "page_name": "Barber 1",
            "ig_username": "barber.1",
        },
    )

    resp = client.get("/v1/instagram/status")

    body = resp.json()
    assert body["connected"] is True
    assert body["page_name"] == "Barber 1"
    assert body["ig_username"] == "barber.1"


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
