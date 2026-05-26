"""Tests for email_service orchestration.

Focus is on the contract around the send: did we resolve the right recipient,
did we pass the right rendered email through, and — critically — does the
service never raise even when Resend or auth fails?
"""

from typing import Any

import pytest

from app.services import email_service

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _stub_resend(
    monkeypatch: pytest.MonkeyPatch, *, configured: bool = True
) -> list[dict[str, Any]]:
    """Replace resend_client.send with a recorder; toggle configured state."""
    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(email_service.resend_client, "is_configured", lambda: configured)

    def fake_send(**kwargs: Any) -> str | None:
        sent.append(kwargs)
        return "msg_id_test"

    monkeypatch.setattr(email_service.resend_client, "send", fake_send)
    return sent


def _stub_owner_lookup(
    monkeypatch: pytest.MonkeyPatch, *, user_id: str | None, email: str | None
) -> None:
    monkeypatch.setattr(
        email_service.tenant_members, "get_owner_user_id", lambda _tid: user_id
    )
    monkeypatch.setattr(
        email_service.users, "get_email_by_user_id", lambda _uid: email
    )


def _tenant(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"id": "t-1", "name": "ACME Barber", "plan": "loyalty"}
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# send_welcome — uses provided email arg, skips when missing
# ---------------------------------------------------------------------------


def test_send_welcome_passes_email_through(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _stub_resend(monkeypatch)

    email_service.send_welcome(tenant=_tenant(), email="owner@acme.test")

    assert len(sent) == 1
    assert sent[0]["to"] == "owner@acme.test"
    assert "Welcome to SmartTap" in sent[0]["subject"]
    assert sent[0]["html"]
    assert sent[0]["text"]
    # Tagging for Resend dashboard filtering.
    assert {"name": "event", "value": "welcome"} in sent[0]["tags"]


def test_send_welcome_skips_when_no_email(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anonymous signup path (email None on the JWT) shouldn't crash. Just
    log and move on."""
    sent = _stub_resend(monkeypatch)
    email_service.send_welcome(tenant=_tenant(), email=None)
    assert sent == []


def test_send_welcome_noops_when_resend_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dev/CI without RESEND_API_KEY: production code runs the same, no send."""
    sent = _stub_resend(monkeypatch, configured=False)
    email_service.send_welcome(tenant=_tenant(), email="owner@acme.test")
    assert sent == []


# ---------------------------------------------------------------------------
# send_payment_succeeded — resolves via owner lookup
# ---------------------------------------------------------------------------


def test_send_payment_succeeded_resolves_owner_and_includes_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent = _stub_resend(monkeypatch)
    _stub_owner_lookup(monkeypatch, user_id="user-1", email="owner@acme.test")

    email_service.send_payment_succeeded(
        tenant_id="t-1",
        tenant=_tenant(),
        session={"amount_total": 5900, "currency": "eur"},
    )

    assert len(sent) == 1
    assert sent[0]["to"] == "owner@acme.test"
    assert "€59.00" in sent[0]["text"]
    assert {"name": "event", "value": "payment_succeeded"} in sent[0]["tags"]


def test_send_payment_succeeded_skips_when_owner_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tenant with no owner member (shouldn't happen, but guard) — no send."""
    sent = _stub_resend(monkeypatch)
    _stub_owner_lookup(monkeypatch, user_id=None, email=None)

    email_service.send_payment_succeeded(
        tenant_id="t-1",
        tenant=_tenant(),
        session={"amount_total": 5900, "currency": "eur"},
    )
    assert sent == []


def test_send_payment_succeeded_skips_when_user_has_no_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User exists in auth but has no email (theoretically possible if
    auth.users was edited directly). Don't blow up."""
    sent = _stub_resend(monkeypatch)
    _stub_owner_lookup(monkeypatch, user_id="user-1", email=None)

    email_service.send_payment_succeeded(
        tenant_id="t-1",
        tenant=_tenant(),
        session={"amount_total": 5900, "currency": "eur"},
    )
    assert sent == []


# ---------------------------------------------------------------------------
# send_payment_failed
# ---------------------------------------------------------------------------


def test_send_payment_failed_includes_amount_due(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent = _stub_resend(monkeypatch)
    _stub_owner_lookup(monkeypatch, user_id="user-1", email="owner@acme.test")

    email_service.send_payment_failed(
        tenant_id="t-1",
        tenant=_tenant(),
        invoice={"amount_due": 2900, "currency": "eur", "attempt_count": 1},
    )

    assert len(sent) == 1
    assert "€29.00" in sent[0]["text"]


# ---------------------------------------------------------------------------
# send_subscription_canceled
# ---------------------------------------------------------------------------


def test_send_subscription_canceled_targets_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent = _stub_resend(monkeypatch)
    _stub_owner_lookup(monkeypatch, user_id="user-1", email="owner@acme.test")

    email_service.send_subscription_canceled(tenant_id="t-1", tenant=_tenant())

    assert len(sent) == 1
    assert "canceled" in sent[0]["subject"].lower()


# ---------------------------------------------------------------------------
# Failure containment — the most important contract
# ---------------------------------------------------------------------------


def test_resend_failure_does_not_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    """If Resend raises, the caller (webhook handler) must NOT see the
    exception. Otherwise Stripe will retry the webhook just because the
    email server hiccupped — wrong control loop."""
    monkeypatch.setattr(email_service.resend_client, "is_configured", lambda: True)
    monkeypatch.setattr(
        email_service.resend_client,
        "send",
        lambda **_kw: (_ for _ in ()).throw(RuntimeError("resend down")),
    )

    # Must not raise.
    email_service.send_welcome(tenant=_tenant(), email="owner@acme.test")


def test_owner_lookup_failure_inside_users_module_is_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The contract is: users.get_email_by_user_id swallows its own errors
    and returns None. This test pins that contract by importing the real
    function and patching only the deep dependency it calls."""
    from app.db import users

    class FakeAdminClient:
        @property
        def auth(self) -> Any:
            return self

        @property
        def admin(self) -> Any:
            return self

        def get_user_by_id(self, _uid: str) -> Any:
            raise RuntimeError("auth admin down")

    monkeypatch.setattr(
        users, "get_supabase_admin", lambda: FakeAdminClient()
    )

    # The function itself must not raise; it returns None on failure.
    assert users.get_email_by_user_id("user-1") is None
