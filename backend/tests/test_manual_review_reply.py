"""Tests for the manual review-reply path (Places bridge replacement).

The owner pastes a review into the dashboard; Claude drafts a reply using
tenant context + few-shot examples of previously approved replies. On copy,
the review is stored as source='manual', status='approved'.
"""

from typing import Any

import pytest

from app.errors import BusinessError
from app.services import review_response_service as svc

TENANT = "t-1"


@pytest.fixture
def stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {
        "tenant": {
            "id": TENANT,
            "name": "ACME Barbers",
            "business_type": "barbershop",
            "opening_hours": "Mon-Sat 9-18",
            "menu_info": "Cuts, fades, beard trims",
            "brand_voice": "Friendly and casual",
        },
        "examples": [],
        "anthropic_ok": True,
        "captured": {},
        "created": [],
    }

    monkeypatch.setattr(svc.tenants, "get_by_id", lambda tid: state["tenant"])
    monkeypatch.setattr(
        svc.reviews, "list_reply_examples", lambda tid, **kw: state["examples"]
    )
    monkeypatch.setattr(
        svc.anthropic_client, "is_configured", lambda: state["anthropic_ok"]
    )

    def fake_generate(**kw: Any) -> str:
        state["captured"] = kw
        return "DRAFT REPLY"

    monkeypatch.setattr(svc.anthropic_client, "generate_text", fake_generate)

    def fake_create(**kw: Any) -> dict[str, Any]:
        state["created"].append(kw)
        return {"id": "r-manual", **kw}

    monkeypatch.setattr(svc.reviews, "create", fake_create)

    def fake_update(rid: str, fields: dict[str, Any]) -> dict[str, Any]:
        state["created"][-1].update(fields)
        return {"id": rid, **state["created"][-1]}

    monkeypatch.setattr(svc.reviews, "update", fake_update)
    return state


# ---------------------------------------------------------------------------
# generate_manual_reply
# ---------------------------------------------------------------------------


def test_generate_returns_draft_and_uses_tenant_context(stubs: dict[str, Any]) -> None:
    draft = svc.generate_manual_reply(
        TENANT, comment="Great cut!", rating=5, author="Alex"
    )
    assert draft == "DRAFT REPLY"
    system = stubs["captured"]["system"]
    assert "ACME Barbers" in system
    assert "Mon-Sat 9-18" in system
    assert "Cuts, fades, beard trims" in system
    assert "Friendly and casual" in system
    assert "Alex left a 5-star review" in stubs["captured"]["user_text"]


def test_generate_omits_missing_context_lines(stubs: dict[str, Any]) -> None:
    stubs["tenant"] = {"id": TENANT, "name": "ACME", "business_type": "cafe"}
    svc.generate_manual_reply(TENANT, comment="ok", rating=3, author=None)
    system = stubs["captured"]["system"]
    assert "Opening hours" not in system
    assert "Brand voice" not in system


def test_generate_few_shot_prioritises_similar_rating(stubs: dict[str, Any]) -> None:
    stubs["examples"] = [
        {"rating": 5, "comment": "five", "reply_text": "REPLY-FIVE"},
        {"rating": 1, "comment": "one", "reply_text": "REPLY-ONE"},
        {"rating": 2, "comment": "two", "reply_text": "REPLY-TWO"},
    ]
    svc.generate_manual_reply(TENANT, comment="bad", rating=1, author=None)
    system = stubs["captured"]["system"]
    # 1★ target: the 1★ and 2★ examples must rank before the 5★ one.
    assert system.index("REPLY-ONE") < system.index("REPLY-FIVE")
    assert system.index("REPLY-TWO") < system.index("REPLY-FIVE")


def test_generate_caps_examples_at_four(stubs: dict[str, Any]) -> None:
    stubs["examples"] = [
        {"rating": 4, "comment": f"c{i}", "reply_text": f"REPLY-{i}"} for i in range(6)
    ]
    svc.generate_manual_reply(TENANT, comment="nice", rating=4, author=None)
    system = stubs["captured"]["system"]
    assert sum(1 for i in range(6) if f"REPLY-{i}" in system) == 4


def test_generate_no_examples_no_example_block(stubs: dict[str, Any]) -> None:
    svc.generate_manual_reply(TENANT, comment="hi", rating=4, author=None)
    assert "approved before" not in stubs["captured"]["system"]


def test_generate_unconfigured_raises_business_error(stubs: dict[str, Any]) -> None:
    stubs["anthropic_ok"] = False
    with pytest.raises(BusinessError):
        svc.generate_manual_reply(TENANT, comment="hi", rating=5, author=None)


# ---------------------------------------------------------------------------
# save_manual_review
# ---------------------------------------------------------------------------


def test_save_stores_manual_approved(stubs: dict[str, Any]) -> None:
    row = svc.save_manual_review(
        TENANT,
        comment="Great cut!",
        rating=5,
        author="Alex",
        ai_draft="DRAFT REPLY",
        reply_text="Thanks Alex! See you soon.",
    )
    assert row["id"] == "r-manual"
    created = stubs["created"][0]
    assert created["source"] == "manual"
    assert created["status"] == "approved"
    assert created["google_review_id"] is None
    assert created["reply_text"] == "Thanks Alex! See you soon."


def test_cron_prompt_still_has_tenant_context(stubs: dict[str, Any]) -> None:
    # The GBP cron path shares the enriched system prompt (free improvement).
    draft = svc.generate_draft(
        stubs["tenant"], {"rating": 5, "author": "Sam", "comment": "great"}
    )
    assert draft == "DRAFT REPLY"
    assert "Mon-Sat 9-18" in stubs["captured"]["system"]
