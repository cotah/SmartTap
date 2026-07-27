"""Tests for the stale-connection retry on the Supabase (postgrest) client.

Supabase's edge (Cloudflare) drops idle keep-alive connections; httpx then
raises RemoteProtocolError("Server disconnected") when it reuses one.
postgrest's own send_with_retry only covers HTTP 503/520 responses, so the
exception propagated as a 500. We retry exactly once, safe methods only.
"""

from typing import Any

import httpx
import pytest

from app.services import supabase_client


class _FlakyTransport(httpx.BaseTransport):
    """Raises RemoteProtocolError on the first request, then succeeds."""

    def __init__(self) -> None:
        self.calls = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self.calls == 1:
            raise httpx.RemoteProtocolError("Server disconnected")
        return httpx.Response(200, json=[])


def test_retries_get_once_on_remote_protocol_error() -> None:
    inner = _FlakyTransport()
    transport = supabase_client._RetryOnStaleConnectionTransport(inner)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        resp = client.get("/rest/v1/tenants")

    assert resp.status_code == 200
    assert inner.calls == 2


def test_does_not_retry_post() -> None:
    """Writes must not retry — the server could have applied the change
    before the connection died, and a retry would double-apply it."""
    inner = _FlakyTransport()
    transport = supabase_client._RetryOnStaleConnectionTransport(inner)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        with pytest.raises(httpx.RemoteProtocolError):
            client.post("/rest/v1/stamps", json={})

    assert inner.calls == 1


def test_get_supabase_admin_installs_retry_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class S:
        supabase_url = "https://example.supabase.co"
        supabase_service_role_key = "svc-key"

    monkeypatch.setattr(supabase_client, "get_settings", lambda: S())
    supabase_client.get_supabase_admin.cache_clear()
    try:
        client: Any = supabase_client.get_supabase_admin()
        assert isinstance(
            client.postgrest.session._transport,
            supabase_client._RetryOnStaleConnectionTransport,
        )
    finally:
        supabase_client.get_supabase_admin.cache_clear()
