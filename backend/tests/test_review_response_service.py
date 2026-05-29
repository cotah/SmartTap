"""Tests for the review-response service (S5 Feature 3, Phase A).

Covers the cron (dedupe, draft-only-for-new, no-op without Anthropic, error
isolation) and publish_review (text precedence, scope, no-op/failed handling).
Google + Anthropic + DB layers are stubbed.
"""

from typing import Any

import pytest

from app.errors import BusinessError, NotFoundError
from app.services import review_response_service as svc

TENANT = "t-1"


@pytest.fixture
def stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {
        "connections": [
            {"tenant_id": TENANT, "refresh_token": "rt", "account_id": "a", "location_id": "l"}
        ],
        "fetched": [],
        "existing": set(),
        "created": [],
        "anthropic_ok": True,
        "publish_ok": True,
        "publish_raises": False,
        "owned": None,
        "connection": {"tenant_id": TENANT, "refresh_token": "rt"},
        "updates": [],
        "published": [],
    }

    monkeypatch.setattr(svc.google_connections, "list_connected", lambda: state["connections"])
    monkeypatch.setattr(svc.google_connections, "get_by_tenant", lambda tid: state["connection"])
    monkeypatch.setattr(svc.google_client, "list_new_reviews", lambda conn: state["fetched"])
    monkeypatch.setattr(
        svc.tenants,
        "get_by_id",
        lambda tid: {"id": tid, "name": "ACME", "business_type": "barbershop"},
    )

    monkeypatch.setattr(svc.reviews, "exists", lambda tid, gid: gid in state["existing"])

    def fake_create(**kw: Any) -> dict[str, Any]:
        state["created"].append(kw)
        return {"id": "r-new", **kw}

    monkeypatch.setattr(svc.reviews, "create", fake_create)
    monkeypatch.setattr(svc.reviews, "get_owned", lambda tid, rid: state["owned"])

    def fake_update(rid: str, fields: dict[str, Any]) -> dict[str, Any]:
        state["updates"].append((rid, fields))
        return {"id": rid, **fields}

    monkeypatch.setattr(svc.reviews, "update", fake_update)

    def fake_mark_published(rid: str, text: str, when: Any) -> dict[str, Any]:
        state["published"].append((rid, text))
        return {"id": rid, "status": "published", "reply_text": text}

    monkeypatch.setattr(svc.reviews, "mark_published", fake_mark_published)

    monkeypatch.setattr(svc.anthropic_client, "is_configured", lambda: state["anthropic_ok"])
    monkeypatch.setattr(svc.anthropic_client, "generate_text", lambda **kw: "DRAFT REPLY")

    def fake_publish(conn: Any, gid: str, text: str) -> bool:
        if state["publish_raises"]:
            raise RuntimeError("google 500")
        return state["publish_ok"]

    monkeypatch.setattr(svc.google_client, "publish_reply", fake_publish)
    return state


# ---------------------------------------------------------------------------
# Cron
# ---------------------------------------------------------------------------


def test_cron_drafts_only_new_reviews(stubs: dict[str, Any]) -> None:
    stubs["fetched"] = [
        {"google_review_id": "g1", "author": "Alex", "rating": 5, "comment": "great", "created_at_google": "2026-05-01T10:00:00Z"},  # noqa: E501
        {"google_review_id": "g2", "author": "Sam", "rating": 2, "comment": "slow", "created_at_google": "2026-05-02T10:00:00Z"},  # noqa: E501
    ]
    stubs["existing"] = {"g1"}  # already drafted

    result = svc.run_daily()

    assert result.tenants_scanned == 1
    assert result.reviews_drafted == 1  # only g2
    assert len(stubs["created"]) == 1
    created = stubs["created"][0]
    assert created["google_review_id"] == "g2"
    assert created["ai_draft"] == "DRAFT REPLY"
    assert created["status"] == "pending"


def test_cron_stores_pending_without_anthropic(stubs: dict[str, Any]) -> None:
    stubs["anthropic_ok"] = False
    stubs["fetched"] = [{"google_review_id": "g9", "rating": 4, "comment": "ok"}]

    result = svc.run_daily()

    assert result.reviews_drafted == 1
    assert stubs["created"][0]["ai_draft"] is None  # no draft, still pending
    assert stubs["created"][0]["status"] == "pending"


def test_cron_no_connections_returns_zero(stubs: dict[str, Any]) -> None:
    stubs["connections"] = []
    result = svc.run_daily()
    assert result.tenants_scanned == 0
    assert result.reviews_drafted == 0


def test_cron_error_on_one_review_is_isolated(
    stubs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    stubs["fetched"] = [
        {"google_review_id": "g1", "rating": 5},
        {"google_review_id": "g2", "rating": 5},
    ]

    calls: list[str] = []

    def flaky_create(**kw: Any) -> dict[str, Any]:
        calls.append(kw["google_review_id"])
        if kw["google_review_id"] == "g1":
            raise RuntimeError("db down")
        return {"id": "r", **kw}

    monkeypatch.setattr(svc.reviews, "create", flaky_create)

    result = svc.run_daily()

    assert calls == ["g1", "g2"]  # didn't stop on g1
    assert result.reviews_drafted == 1
    assert any("g1" in e for e in result.errors)


# ---------------------------------------------------------------------------
# publish_review
# ---------------------------------------------------------------------------


def test_publish_not_found_raises(stubs: dict[str, Any]) -> None:
    stubs["owned"] = None
    with pytest.raises(NotFoundError):
        svc.publish_review(tenant_id=TENANT, review_id="missing")


def test_publish_no_text_raises(stubs: dict[str, Any]) -> None:
    stubs["owned"] = {"id": "r1", "google_review_id": "g1", "reply_text": None, "ai_draft": None}
    with pytest.raises(BusinessError):
        svc.publish_review(tenant_id=TENANT, review_id="r1")


def test_publish_prefers_reply_text_over_draft(stubs: dict[str, Any]) -> None:
    stubs["owned"] = {
        "id": "r1", "google_review_id": "g1", "reply_text": "edited", "ai_draft": "draft"
    }
    svc.publish_review(tenant_id=TENANT, review_id="r1")
    assert stubs["published"] == [("r1", "edited")]


def test_publish_falls_back_to_draft(stubs: dict[str, Any]) -> None:
    stubs["owned"] = {
        "id": "r1", "google_review_id": "g1", "reply_text": None, "ai_draft": "the draft"
    }
    svc.publish_review(tenant_id=TENANT, review_id="r1")
    assert stubs["published"] == [("r1", "the draft")]


def test_publish_noop_marks_failed_and_raises(stubs: dict[str, Any]) -> None:
    # publish_reply returns False (API not live) -> failed + BusinessError.
    stubs["publish_ok"] = False
    stubs["owned"] = {"id": "r1", "google_review_id": "g1", "reply_text": "hi", "ai_draft": None}
    with pytest.raises(BusinessError):
        svc.publish_review(tenant_id=TENANT, review_id="r1")
    assert any(fields.get("status") == "failed" for _, fields in stubs["updates"])


def test_publish_api_exception_marks_failed(stubs: dict[str, Any]) -> None:
    stubs["publish_raises"] = True
    stubs["owned"] = {"id": "r1", "google_review_id": "g1", "reply_text": "hi", "ai_draft": None}
    with pytest.raises(BusinessError):
        svc.publish_review(tenant_id=TENANT, review_id="r1")
    assert any(fields.get("status") == "failed" for _, fields in stubs["updates"])


def test_publish_not_connected_raises(stubs: dict[str, Any]) -> None:
    stubs["owned"] = {"id": "r1", "google_review_id": "g1", "reply_text": "hi", "ai_draft": None}
    stubs["connection"] = None
    with pytest.raises(BusinessError):
        svc.publish_review(tenant_id=TENANT, review_id="r1")
