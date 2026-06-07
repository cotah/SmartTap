"""Tests for the Twilio SMS client (Sprint 5.6).

The only behaviour worth pinning without a live Twilio account is the
build-to-activate gate: no credentials → no send, no crash.
"""

import pytest

from app.config import get_settings
from app.services import twilio_sms_client


def test_not_configured_without_credentials() -> None:
    get_settings.cache_clear()
    assert twilio_sms_client.is_configured() is False


def test_send_sms_is_a_noop_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No credentials → returns None and never touches the network."""
    monkeypatch.setattr(twilio_sms_client, "is_configured", lambda: False)

    def _boom(*_a: object, **_k: object) -> object:  # pragma: no cover
        raise AssertionError("must not hit the network when unconfigured")

    monkeypatch.setattr(twilio_sms_client.httpx, "post", _boom)

    assert twilio_sms_client.send_sms(to="+353871234567", body="hi") is None
