"""Tests for the Instagram DM auto-reply service.

Stubs every collaborator (meta_connections, tenants, anthropic_client,
meta_client, instagram_interactions) so we exercise the decision flow:
tenant lookup, prompt building, reply/send, and interaction logging.
The service must NEVER raise — the webhook has to 200.
"""

from typing import Any

import pytest

from app.services import instagram_dm_service
from app.services.instagram_dm_service import InstagramEvent

IG_ACCOUNT = "17841400000000001"
TENANT_ID = "11111111-1111-1111-1111-111111111111"


def _dm(text: str | None = "what time do you open?", *, story: bool = False) -> InstagramEvent:
    return InstagramEvent(
        ig_account_id=IG_ACCOUNT, sender_id="9876", text=text, is_story_mention=story
    )


@pytest.fixture
def stub_all(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Happy-path stubs. Tests flip individual keys to exercise failure paths."""
    state: dict[str, Any] = {
        "conn": {
            "tenant_id": TENANT_ID,
            "instagram_business_account_id": IG_ACCOUNT,
            "page_access_token": "PAGE_TOKEN",
        },
        "tenant": {
            "id": TENANT_ID,
            "name": "Dublin Cuts",
            "business_type": "barbershop",
            "opening_hours": "Mon-Sat 9-18",
            "menu_info": "Skin fade €25",
            "brand_voice": "casual, friendly",
        },
        "configured": True,
        "reply": "We open at 9am!",
        "send_ok": True,
        "sent": [],
        "logged": [],
        "prompts": [],
    }

    monkeypatch.setattr(
        instagram_dm_service.meta_connections,
        "get_by_ig_account",
        lambda ig_account_id: state["conn"],
    )
    monkeypatch.setattr(
        instagram_dm_service.tenants, "get_by_id", lambda tenant_id: state["tenant"]
    )
    monkeypatch.setattr(
        instagram_dm_service.anthropic_client, "is_configured", lambda: state["configured"]
    )

    def fake_generate(*, system: str, user_text: str, max_tokens: int) -> str | None:
        state["prompts"].append({"system": system, "user_text": user_text})
        return state["reply"]

    monkeypatch.setattr(instagram_dm_service.anthropic_client, "generate_text", fake_generate)

    def fake_send(**kw: Any) -> bool:
        state["sent"].append(kw)
        return state["send_ok"]

    monkeypatch.setattr(instagram_dm_service.meta_client, "send_dm", fake_send)
    monkeypatch.setattr(
        instagram_dm_service.instagram_interactions,
        "create",
        lambda **kw: state["logged"].append(kw),
    )
    return state


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_text_dm_answered_and_logged(stub_all: dict[str, Any]) -> None:
    instagram_dm_service.handle_event(_dm())

    assert stub_all["sent"] == [
        {
            "ig_business_account_id": IG_ACCOUNT,
            "page_access_token": "PAGE_TOKEN",
            "recipient_id": "9876",
            "text": "We open at 9am!",
        }
    ]
    assert stub_all["logged"] == [
        {
            "tenant_id": TENANT_ID,
            "interaction_type": "dm",
            "external_sender_id": "9876",
            "incoming_text": "what time do you open?",
            "reply_text": "We open at 9am!",
            "status": "answered",
        }
    ]


def test_prompt_includes_tenant_context(stub_all: dict[str, Any]) -> None:
    instagram_dm_service.handle_event(_dm())

    system = stub_all["prompts"][0]["system"]
    assert "Dublin Cuts" in system
    assert "barbershop" in system
    assert "Mon-Sat 9-18" in system
    assert "Skin fade €25" in system
    assert "casual, friendly" in system


def test_story_mention_logged_with_type_and_thanks(stub_all: dict[str, Any]) -> None:
    instagram_dm_service.handle_event(_dm(None, story=True))

    assert "thanking them for the mention" in stub_all["prompts"][0]["system"]
    assert "Instagram story" in stub_all["prompts"][0]["user_text"]
    assert stub_all["logged"][0]["interaction_type"] == "story_mention"
    assert stub_all["logged"][0]["status"] == "answered"


# ---------------------------------------------------------------------------
# Skips
# ---------------------------------------------------------------------------


def test_unknown_ig_account_is_skipped(stub_all: dict[str, Any]) -> None:
    stub_all["conn"] = None
    instagram_dm_service.handle_event(_dm())
    assert stub_all["sent"] == []
    assert stub_all["logged"] == []


def test_non_text_dm_is_skipped(stub_all: dict[str, Any]) -> None:
    # Image/audio DM without text and without story mention — out of scope v1.
    instagram_dm_service.handle_event(_dm(None))
    assert stub_all["sent"] == []
    assert stub_all["logged"] == []


def test_anthropic_not_configured_logs_failed_without_send(stub_all: dict[str, Any]) -> None:
    stub_all["configured"] = False
    instagram_dm_service.handle_event(_dm())
    assert stub_all["sent"] == []
    assert stub_all["logged"][0]["status"] == "failed"
    assert stub_all["logged"][0]["reply_text"] is None


# ---------------------------------------------------------------------------
# Failure paths — must never raise
# ---------------------------------------------------------------------------


def test_send_failure_logs_failed(stub_all: dict[str, Any]) -> None:
    stub_all["send_ok"] = False
    instagram_dm_service.handle_event(_dm())
    assert stub_all["logged"][0]["status"] == "failed"
    assert stub_all["logged"][0]["reply_text"] == "We open at 9am!"


def test_generate_exception_logs_failed(
    stub_all: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(**kw: Any) -> str:
        raise RuntimeError("api down")

    monkeypatch.setattr(instagram_dm_service.anthropic_client, "generate_text", boom)
    instagram_dm_service.handle_event(_dm())  # must not raise
    assert stub_all["sent"] == []
    assert stub_all["logged"][0]["status"] == "failed"


def test_interaction_log_failure_does_not_raise(
    stub_all: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(**kw: Any) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(instagram_dm_service.instagram_interactions, "create", boom)
    instagram_dm_service.handle_event(_dm())  # must not raise
    assert stub_all["sent"]  # reply still went out before the log failed
