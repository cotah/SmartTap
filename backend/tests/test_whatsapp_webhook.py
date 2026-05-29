"""Tests for the Meta WhatsApp webhook route (S5 Feature 1).

Uses the real app via TestClient but stubs the WhatsApp client (signature /
verify-token / send) and the bot service, so we exercise routing, parsing, and
status codes without HMAC or external calls.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import webhooks

client = TestClient(app)


@pytest.fixture
def stub_client(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch the WhatsApp client + bot service the router calls. Returns a dict
    the test can flip (signature_ok / verify_ok) and inspect (sent, dispatched)."""
    state: dict[str, Any] = {"signature_ok": True, "verify_ok": True, "sent": [], "dispatched": []}

    monkeypatch.setattr(
        webhooks.whatsapp_client, "validate_signature", lambda **kw: state["signature_ok"]
    )
    monkeypatch.setattr(
        webhooks.whatsapp_client, "verify_token_matches", lambda token: state["verify_ok"]
    )
    monkeypatch.setattr(
        webhooks.whatsapp_client,
        "send_text",
        lambda **kw: state["sent"].append(kw),
    )

    def fake_handle(from_number: str, body: str) -> str:
        state["dispatched"].append((from_number, body))
        return f"reply to {body}"

    monkeypatch.setattr(webhooks.whatsapp_bot_service, "handle_inbound", fake_handle)
    return state


def _text_payload(from_number: str, body: str) -> dict[str, Any]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "PNID"},
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": "wamid.X",
                                    "type": "text",
                                    "text": {"body": body},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# GET verification handshake
# ---------------------------------------------------------------------------


def test_get_verify_returns_challenge_when_token_matches(stub_client: dict[str, Any]) -> None:
    stub_client["verify_ok"] = True
    resp = client.get(
        "/v1/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "98765"},
    )
    assert resp.status_code == 200
    assert resp.text == "98765"


def test_get_verify_403_when_token_wrong(stub_client: dict[str, Any]) -> None:
    stub_client["verify_ok"] = False
    resp = client.get(
        "/v1/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "bad", "hub.challenge": "1"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST inbound
# ---------------------------------------------------------------------------


def test_post_invalid_signature_403(stub_client: dict[str, Any]) -> None:
    stub_client["signature_ok"] = False
    resp = client.post("/v1/webhooks/whatsapp", json=_text_payload("353871234567", "hi"))
    assert resp.status_code == 403
    assert stub_client["dispatched"] == []


def test_post_text_message_dispatches_and_replies(stub_client: dict[str, Any]) -> None:
    resp = client.post(
        "/v1/webhooks/whatsapp", json=_text_payload("353871234567", "quantos clientes?")
    )
    assert resp.status_code == 200
    assert stub_client["dispatched"] == [("353871234567", "quantos clientes?")]
    assert stub_client["sent"] == [{"to": "353871234567", "body": "reply to quantos clientes?"}]


def test_post_status_callback_is_ignored(stub_client: dict[str, Any]) -> None:
    # Delivery/read callbacks carry `statuses`, no `messages` — ack, don't dispatch.
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {"field": "messages", "value": {"statuses": [{"status": "delivered"}]}}
                ]
            }
        ],
    }
    resp = client.post("/v1/webhooks/whatsapp", json=payload)
    assert resp.status_code == 200
    assert stub_client["dispatched"] == []
    assert stub_client["sent"] == []


# ---------------------------------------------------------------------------
# Payload parsing
# ---------------------------------------------------------------------------


def test_extract_text_messages_parses_and_skips_non_text() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": "111", "type": "text", "text": {"body": "hello"}},
                                {"from": "222", "type": "image", "image": {"id": "x"}},
                            ]
                        }
                    }
                ]
            }
        ]
    }
    assert webhooks._extract_text_messages(payload) == [("111", "hello")]


def test_extract_text_messages_handles_malformed() -> None:
    assert webhooks._extract_text_messages({}) == []
    assert webhooks._extract_text_messages({"entry": [{}]}) == []
