"""Tests for the Meta Instagram webhook route (Instagram DM assistant).

Uses the real app via TestClient but stubs the Meta client (signature /
verify-token) and the DM service, so we exercise routing, parsing, and
status codes without HMAC or external calls.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import webhooks
from app.services.instagram_dm_service import InstagramEvent

client = TestClient(app)

IG_ACCOUNT = "17841400000000001"
SENDER = "9876543210"


@pytest.fixture
def stub_meta(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch the Meta client + DM service the router calls. Returns a dict
    the test can flip (signature_ok / verify_ok) and inspect (handled)."""
    state: dict[str, Any] = {"signature_ok": True, "verify_ok": True, "handled": []}

    monkeypatch.setattr(
        webhooks.meta_client, "validate_signature", lambda **kw: state["signature_ok"]
    )
    monkeypatch.setattr(
        webhooks.meta_client, "verify_token_matches", lambda token: state["verify_ok"]
    )
    monkeypatch.setattr(
        webhooks.instagram_dm_service,
        "handle_event",
        lambda event: state["handled"].append(event),
    )
    return state


def _dm_payload(
    text: str | None = "hi there",
    *,
    is_echo: bool = False,
    attachments: list[dict[str, Any]] | None = None,
    sender_id: str = SENDER,
) -> dict[str, Any]:
    message: dict[str, Any] = {}
    if text is not None:
        message["text"] = text
    if is_echo:
        message["is_echo"] = True
    if attachments is not None:
        message["attachments"] = attachments
    return {
        "object": "instagram",
        "entry": [
            {
                "id": IG_ACCOUNT,
                "time": 1721990400,
                "messaging": [
                    {
                        "sender": {"id": sender_id},
                        "recipient": {"id": IG_ACCOUNT},
                        "message": message,
                    }
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# GET verification handshake
# ---------------------------------------------------------------------------


def test_get_verify_returns_challenge_when_token_matches(stub_meta: dict[str, Any]) -> None:
    stub_meta["verify_ok"] = True
    resp = client.get(
        "/v1/webhooks/instagram",
        params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "13579"},
    )
    assert resp.status_code == 200
    assert resp.text == "13579"


def test_get_verify_403_when_token_wrong(stub_meta: dict[str, Any]) -> None:
    stub_meta["verify_ok"] = False
    resp = client.get(
        "/v1/webhooks/instagram",
        params={"hub.mode": "subscribe", "hub.verify_token": "bad", "hub.challenge": "1"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST inbound
# ---------------------------------------------------------------------------


def test_post_invalid_signature_403(stub_meta: dict[str, Any]) -> None:
    stub_meta["signature_ok"] = False
    resp = client.post("/v1/webhooks/instagram", json=_dm_payload("hello"))
    assert resp.status_code == 403
    assert stub_meta["handled"] == []


def test_post_text_dm_dispatches(stub_meta: dict[str, Any]) -> None:
    resp = client.post("/v1/webhooks/instagram", json=_dm_payload("do you open Sundays?"))
    assert resp.status_code == 200
    assert stub_meta["handled"] == [
        InstagramEvent(
            ig_account_id=IG_ACCOUNT,
            sender_id=SENDER,
            text="do you open Sundays?",
            is_story_mention=False,
        )
    ]


def test_post_story_mention_dispatches_with_flag(stub_meta: dict[str, Any]) -> None:
    payload = _dm_payload(
        None, attachments=[{"type": "story_mention", "payload": {"url": "https://cdn/x"}}]
    )
    resp = client.post("/v1/webhooks/instagram", json=payload)
    assert resp.status_code == 200
    assert stub_meta["handled"] == [
        InstagramEvent(
            ig_account_id=IG_ACCOUNT, sender_id=SENDER, text=None, is_story_mention=True
        )
    ]


def test_post_echo_is_ignored(stub_meta: dict[str, Any]) -> None:
    # Echoes of our own outbound replies must be skipped (anti-loop).
    resp = client.post("/v1/webhooks/instagram", json=_dm_payload("our reply", is_echo=True))
    assert resp.status_code == 200
    assert stub_meta["handled"] == []


def test_post_own_account_sender_is_ignored(stub_meta: dict[str, Any]) -> None:
    resp = client.post(
        "/v1/webhooks/instagram", json=_dm_payload("self", sender_id=IG_ACCOUNT)
    )
    assert resp.status_code == 200
    assert stub_meta["handled"] == []


def test_post_service_error_still_200(
    stub_meta: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # A bot failure must never 5xx — Meta would retry and duplicate replies.
    def boom(event: InstagramEvent) -> None:
        raise RuntimeError("bot exploded")

    monkeypatch.setattr(webhooks.instagram_dm_service, "handle_event", boom)
    resp = client.post("/v1/webhooks/instagram", json=_dm_payload("hi"))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Payload parsing
# ---------------------------------------------------------------------------


def test_extract_instagram_events_handles_malformed() -> None:
    assert webhooks._extract_instagram_events({}) == []
    assert webhooks._extract_instagram_events({"entry": [{}]}) == []
    assert webhooks._extract_instagram_events({"entry": [{"id": IG_ACCOUNT}]}) == []
    assert (
        webhooks._extract_instagram_events(
            {"entry": [{"id": IG_ACCOUNT, "messaging": [{"message": None}]}]}
        )
        == []
    )
    # entry.id must be a string — numeric ids are skipped, not coerced.
    assert (
        webhooks._extract_instagram_events(
            {
                "entry": [
                    {
                        "id": 123,
                        "messaging": [{"sender": {"id": SENDER}, "message": {"text": "x"}}],
                    }
                ]
            }
        )
        == []
    )


def test_extract_instagram_events_multiple_entries() -> None:
    payload = {
        "entry": [
            {
                "id": "acct-1",
                "messaging": [
                    {"sender": {"id": "u1"}, "message": {"text": "one"}},
                    {"sender": {"id": "u2"}, "message": {"text": "our own", "is_echo": True}},
                ],
            },
            {
                "id": "acct-2",
                "messaging": [{"sender": {"id": "u3"}, "message": {"text": "two"}}],
            },
        ]
    }
    events = webhooks._extract_instagram_events(payload)
    assert [(e.ig_account_id, e.sender_id, e.text) for e in events] == [
        ("acct-1", "u1", "one"),
        ("acct-2", "u3", "two"),
    ]
