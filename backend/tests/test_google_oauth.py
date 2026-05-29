"""Tests for the Google OAuth router (S5 Feature 3).

State signing roundtrip + the public callback (token exchange + connection
upsert stubbed). Connect requires auth, so it's covered indirectly via the
state helpers; the callback is public and tested end-to-end via TestClient.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import google_oauth

client = TestClient(app)


@pytest.fixture(autouse=True)
def _secret(monkeypatch: pytest.MonkeyPatch) -> None:
    class S:
        supabase_jwt_secret = "test-secret"
        site_url = "https://smarttap.test"

    monkeypatch.setattr(google_oauth, "get_settings", lambda: S())


def test_state_sign_verify_roundtrip() -> None:
    state = google_oauth._sign_state("tenant-123")
    assert google_oauth._verify_state(state) == "tenant-123"


def test_verify_state_rejects_tampered() -> None:
    state = google_oauth._sign_state("tenant-123")
    tampered = state.replace("tenant-123", "tenant-999")
    assert google_oauth._verify_state(tampered) is None


def test_verify_state_rejects_garbage() -> None:
    assert google_oauth._verify_state("no-dot") is None


def test_callback_success_stores_connection_and_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        google_oauth.google_client, "exchange_code", lambda code: {"refresh_token": "RT-123"}
    )
    monkeypatch.setattr(
        google_oauth.google_connections,
        "upsert",
        lambda **kw: captured.update(kw) or {"id": "c1", **kw},
    )

    state = google_oauth._sign_state("tenant-123")
    resp = client.get(
        "/v1/google/callback", params={"code": "auth-code", "state": state}, follow_redirects=False
    )

    assert resp.status_code == 302
    assert "connected=1" in resp.headers["location"]
    assert captured["tenant_id"] == "tenant-123"
    assert captured["refresh_token"] == "RT-123"


def test_callback_bad_state_redirects_error(monkeypatch: pytest.MonkeyPatch) -> None:
    resp = client.get(
        "/v1/google/callback",
        params={"code": "x", "state": "tenant.badsig"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "connected=0" in resp.headers["location"]


def test_callback_oauth_error_redirects_error() -> None:
    resp = client.get(
        "/v1/google/callback", params={"error": "access_denied"}, follow_redirects=False
    )
    assert resp.status_code == 302
    assert "connected=0" in resp.headers["location"]
