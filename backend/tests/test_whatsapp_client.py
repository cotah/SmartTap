"""Tests for the Meta WhatsApp Cloud API client (S5 Feature 1).

Signature validation and the verify-token handshake are security-critical, so
they're tested against real HMAC; send is checked only for the no-op path
(a real send would hit Graph API).
"""

import hashlib
import hmac

import pytest

from app.services import whatsapp_client


class _Settings:
    whatsapp_access_token = ""
    whatsapp_phone_number_id = ""
    whatsapp_app_secret = ""
    whatsapp_verify_token = ""
    whatsapp_api_version = "v21.0"


def _patch_settings(monkeypatch: pytest.MonkeyPatch, **over: str) -> None:
    s = _Settings()
    for k, v in over.items():
        setattr(s, k, v)
    monkeypatch.setattr(whatsapp_client, "get_settings", lambda: s)


# ---------------------------------------------------------------------------
# is_configured / send no-op
# ---------------------------------------------------------------------------


def test_not_configured_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    assert whatsapp_client.is_configured() is False


def test_send_text_noop_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    # Returns None and makes no HTTP call (httpx.post would raise on network).
    assert whatsapp_client.send_text(to="353871234567", body="hi") is None


def test_send_document_noop_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    assert (
        whatsapp_client.send_document(to="353871234567", content=b"PDF", filename="r.pdf")
        is None
    )


def test_normalise_to_strips_prefixes() -> None:
    assert whatsapp_client._normalise_to("whatsapp:+353871234567") == "353871234567"
    assert whatsapp_client._normalise_to("+353871234567") == "353871234567"
    assert whatsapp_client._normalise_to("353871234567") == "353871234567"


# ---------------------------------------------------------------------------
# Signature validation (X-Hub-Signature-256)
# ---------------------------------------------------------------------------


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, whatsapp_app_secret="topsecret")
    body = b'{"object":"whatsapp_business_account"}'
    sig = _sign("topsecret", body)
    assert whatsapp_client.validate_signature(raw_body=body, signature=sig) is True


def test_invalid_signature_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, whatsapp_app_secret="topsecret")
    body = b'{"a":1}'
    assert whatsapp_client.validate_signature(raw_body=body, signature="sha256=deadbeef") is False


def test_signature_rejected_when_no_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)  # no app secret
    body = b'{"a":1}'
    assert whatsapp_client.validate_signature(raw_body=body, signature=_sign("x", body)) is False


def test_missing_signature_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, whatsapp_app_secret="topsecret")
    assert whatsapp_client.validate_signature(raw_body=b"{}", signature=None) is False


# ---------------------------------------------------------------------------
# Verify-token handshake
# ---------------------------------------------------------------------------


def test_verify_token_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, whatsapp_verify_token="vt-123")
    assert whatsapp_client.verify_token_matches("vt-123") is True
    assert whatsapp_client.verify_token_matches("wrong") is False
    assert whatsapp_client.verify_token_matches(None) is False


def test_verify_token_fails_closed_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)  # no verify token configured
    assert whatsapp_client.verify_token_matches("anything") is False
