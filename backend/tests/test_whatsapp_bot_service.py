"""Tests for the WhatsApp owner bot orchestration (S5 Feature 1, Phase A).

Covers the auth state machine (ask email -> OTP -> verify), anti-enumeration,
attempt limiting / lockout, rate limiting, and the verified -> Claude dispatch.
The whatsapp db is an in-memory fake; users/tenant_members/email/anthropic are
stubbed.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

import app.db.tenants as tenants_db
from app.services import whatsapp_bot_service as svc

NOW = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
# Meta delivers the sender as a wa_id: digits only, no '+' / 'whatsapp:'.
INBOUND = "353871234567"
PHONE = "353871234567"  # _normalise_phone leaves a bare wa_id unchanged
CODE = "001234"  # secrets.randbelow patched to 1234 -> zero-padded to 6


class FakeWhatsappDB:
    def __init__(self) -> None:
        self.links: dict[str, dict[str, Any]] = {}
        self.otps: list[dict[str, Any]] = []
        self._n = 0
        self.clock = NOW

    def get_link_by_phone(self, phone: str) -> dict[str, Any] | None:
        return self.links.get(phone)

    def create_link(self, phone: str, *, state: str = "awaiting_email") -> dict[str, Any]:
        row = {
            "phone": phone,
            "state": state,
            "tenant_id": None,
            "lockout_until": None,
            "pending_email": None,
        }
        self.links[phone] = row
        return row

    def update_link(self, phone: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        if phone in self.links:
            self.links[phone].update(fields)
            return self.links[phone]
        return None

    def create_otp(
        self,
        *,
        phone: str,
        email: str,
        tenant_id: str,
        code_hash: str,
        expires_at: datetime,
    ) -> dict[str, Any]:
        self._n += 1
        row = {
            "id": f"otp-{self._n}",
            "phone": phone,
            "email": email,
            "tenant_id": tenant_id,
            "code_hash": code_hash,
            "expires_at": expires_at.isoformat(),
            "attempts": 0,
            "consumed_at": None,
            "created_at": self.clock.isoformat(),
        }
        self.otps.append(row)
        return row

    def get_latest_otp(self, phone: str) -> dict[str, Any] | None:
        matches = [o for o in self.otps if o["phone"] == phone]
        return matches[-1] if matches else None

    def increment_otp_attempts(self, otp_id: str) -> int:
        for o in self.otps:
            if o["id"] == otp_id:
                o["attempts"] += 1
                return int(o["attempts"])
        return 0

    def consume_otp(self, otp_id: str, when: datetime) -> None:
        for o in self.otps:
            if o["id"] == otp_id:
                o["consumed_at"] = when.isoformat()

    def count_otps_since(self, phone: str, since: datetime) -> int:
        return sum(
            1
            for o in self.otps
            if o["phone"] == phone and datetime.fromisoformat(o["created_at"]) >= since
        )

    def set_pending_action(self, phone: str, action: dict[str, Any], expires_at: datetime) -> None:
        self.update_link(
            phone,
            {"pending_action": action, "pending_action_expires_at": expires_at.isoformat()},
        )

    def clear_pending_action(self, phone: str) -> None:
        self.update_link(phone, {"pending_action": None, "pending_action_expires_at": None})


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> FakeWhatsappDB:
    fake = FakeWhatsappDB()
    for name in (
        "get_link_by_phone",
        "create_link",
        "update_link",
        "create_otp",
        "get_latest_otp",
        "increment_otp_attempts",
        "consume_otp",
        "count_otps_since",
        "set_pending_action",
        "clear_pending_action",
    ):
        monkeypatch.setattr(svc.whatsapp, name, getattr(fake, name))
    # Deterministic OTP code.
    monkeypatch.setattr(svc.secrets, "randbelow", lambda n: 1234)
    return fake


@pytest.fixture
def emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(
        svc.email_service, "send_whatsapp_otp", lambda **kw: sent.append(kw)
    )
    return sent


def _match_owner(monkeypatch: pytest.MonkeyPatch, *, tenant_id: str | None = "t-1") -> None:
    """Make _resolve_tenant_for_email return tenant_id (or None for no match)."""
    if tenant_id is None:
        monkeypatch.setattr(svc.users, "get_user_id_by_email", lambda e: None)
        return
    monkeypatch.setattr(svc.users, "get_user_id_by_email", lambda e: "u-1")
    monkeypatch.setattr(
        svc.tenant_members,
        "list_for_user",
        lambda uid: [{"tenant_id": tenant_id, "role": "owner"}],
    )


# ---------------------------------------------------------------------------
# Auth: ask email
# ---------------------------------------------------------------------------


def test_unknown_number_creates_link_and_asks_email(db: FakeWhatsappDB) -> None:
    reply = svc.handle_inbound(INBOUND, "oi", now=NOW)
    assert reply == svc.MSG_ASK_EMAIL
    assert db.links[PHONE]["state"] == "awaiting_email"


def test_non_email_reprompts(db: FakeWhatsappDB) -> None:
    db.create_link(PHONE, state="awaiting_email")
    reply = svc.handle_inbound(INBOUND, "not an email", now=NOW)
    assert reply == svc.MSG_NOT_AN_EMAIL


# ---------------------------------------------------------------------------
# Auth: email -> OTP
# ---------------------------------------------------------------------------


def test_valid_email_match_sends_otp(
    db: FakeWhatsappDB, emails: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    db.create_link(PHONE, state="awaiting_email")
    _match_owner(monkeypatch, tenant_id="t-1")

    reply = svc.handle_inbound(INBOUND, "owner@shop.ie", now=NOW)

    assert reply == svc.MSG_CODE_SENT
    assert db.links[PHONE]["state"] == "awaiting_code"
    assert len(db.otps) == 1
    assert db.otps[0]["tenant_id"] == "t-1"
    assert emails == [{"to": "owner@shop.ie", "code": CODE}]


def test_unknown_email_is_anti_enumeration(
    db: FakeWhatsappDB, emails: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    db.create_link(PHONE, state="awaiting_email")
    _match_owner(monkeypatch, tenant_id=None)  # no account

    reply = svc.handle_inbound(INBOUND, "stranger@x.com", now=NOW)

    # Identical reply, but nothing actually happened.
    assert reply == svc.MSG_CODE_SENT
    assert db.otps == []
    assert emails == []
    assert db.links[PHONE]["state"] == "awaiting_email"


def test_otp_requests_rate_limited(
    db: FakeWhatsappDB, emails: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    db.create_link(PHONE, state="awaiting_email")
    _match_owner(monkeypatch, tenant_id="t-1")
    # Pre-seed 3 OTPs within the last hour.
    for _ in range(svc.OTP_REQUESTS_PER_HOUR):
        db.create_otp(
            phone=PHONE, email="owner@shop.ie", tenant_id="t-1",
            code_hash="x", expires_at=NOW + timedelta(minutes=10),
        )

    reply = svc.handle_inbound(INBOUND, "owner@shop.ie", now=NOW)

    assert reply == svc.MSG_RATE_LIMITED
    assert len(db.otps) == svc.OTP_REQUESTS_PER_HOUR  # no new OTP
    assert emails == []


# ---------------------------------------------------------------------------
# Auth: verify code
# ---------------------------------------------------------------------------


def _seed_awaiting_code(db: FakeWhatsappDB, *, attempts: int = 0) -> None:
    db.create_link(PHONE, state="awaiting_code")
    db.update_link(PHONE, {"pending_email": "owner@shop.ie"})
    otp = db.create_otp(
        phone=PHONE, email="owner@shop.ie", tenant_id="t-1",
        code_hash=svc._hash_code(CODE), expires_at=NOW + timedelta(minutes=10),
    )
    otp["attempts"] = attempts


def test_correct_code_verifies(db: FakeWhatsappDB) -> None:
    _seed_awaiting_code(db)
    reply = svc.handle_inbound(INBOUND, CODE, now=NOW)
    assert reply == svc.MSG_LINKED
    assert db.links[PHONE]["state"] == "verified"
    assert db.links[PHONE]["tenant_id"] == "t-1"
    assert db.otps[0]["consumed_at"] is not None


def test_wrong_code_decrements_attempts(db: FakeWhatsappDB) -> None:
    _seed_awaiting_code(db)
    reply = svc.handle_inbound(INBOUND, "999999", now=NOW)
    assert "left" in reply.lower()
    assert db.otps[0]["attempts"] == 1
    assert db.links[PHONE]["state"] == "awaiting_code"  # still not verified


def test_fifth_wrong_code_locks_out(db: FakeWhatsappDB) -> None:
    _seed_awaiting_code(db, attempts=4)  # one more wrong = 5
    reply = svc.handle_inbound(INBOUND, "999999", now=NOW)
    assert reply == svc.MSG_LOCKED
    assert db.links[PHONE]["lockout_until"] is not None


def test_expired_code_rejected(db: FakeWhatsappDB) -> None:
    db.create_link(PHONE, state="awaiting_code")
    db.create_otp(
        phone=PHONE, email="o@x.ie", tenant_id="t-1",
        code_hash=svc._hash_code(CODE), expires_at=NOW - timedelta(minutes=1),
    )
    reply = svc.handle_inbound(INBOUND, CODE, now=NOW)
    assert reply == svc.MSG_CODE_EXPIRED


def test_locked_link_short_circuits(db: FakeWhatsappDB) -> None:
    db.create_link(PHONE, state="awaiting_code")
    db.update_link(PHONE, {"lockout_until": (NOW + timedelta(minutes=30)).isoformat()})
    reply = svc.handle_inbound(INBOUND, CODE, now=NOW)
    assert reply == svc.MSG_LOCKED


# ---------------------------------------------------------------------------
# Verified -> Claude dispatch
# ---------------------------------------------------------------------------


def test_verified_dispatches_to_claude(
    db: FakeWhatsappDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    db.create_link(PHONE, state="verified")
    db.update_link(PHONE, {"tenant_id": "t-1"})
    monkeypatch.setattr(
        tenants_db, "get_by_id", lambda tid: {"name": "ACME", "business_type": "barbershop"}
    )
    monkeypatch.setattr(svc.anthropic_client, "is_configured", lambda: True)

    captured: dict[str, Any] = {}

    def fake_run(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "You have 42 customers this week."

    monkeypatch.setattr(svc.anthropic_client, "run_conversation", fake_run)

    reply = svc.handle_inbound(INBOUND, "quantos clientes esta semana?", now=NOW)

    assert reply == "You have 42 customers this week."
    assert captured["user_text"] == "quantos clientes esta semana?"
    # Read tools + write tools are exposed to Claude in Phase B.
    tool_names = {t["name"] for t in captured["tools"]}
    assert "get_overview" in tool_names
    assert "send_reactivation" in tool_names
    # A dispatch closure (scoped to the verified tenant) is handed to Claude.
    assert callable(captured["dispatch"])


def test_verified_but_bot_unconfigured(
    db: FakeWhatsappDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    db.create_link(PHONE, state="verified")
    db.update_link(PHONE, {"tenant_id": "t-1"})
    monkeypatch.setattr(svc.anthropic_client, "is_configured", lambda: False)
    reply = svc.handle_inbound(INBOUND, "hi", now=NOW)
    assert reply == svc.MSG_BOT_UNAVAILABLE


# ---------------------------------------------------------------------------
# Phase B — confirmation gate
# ---------------------------------------------------------------------------


def _verified_with_pending(
    db: FakeWhatsappDB, action: dict[str, Any], *, expires_in_min: int = 5
) -> None:
    db.create_link(PHONE, state="verified")
    db.update_link(
        PHONE,
        {
            "tenant_id": "t-1",
            "pending_action": action,
            "pending_action_expires_at": (
                NOW + timedelta(minutes=expires_in_min)
            ).isoformat(),
        },
    )


def test_confirm_yes_executes_pending(
    db: FakeWhatsappDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    _verified_with_pending(db, {"tool": "send_reactivation"})
    seen: dict[str, Any] = {}

    def fake_exec(tenant_id: str, action: dict[str, Any], *, now: Any) -> str:
        seen["tenant_id"] = tenant_id
        seen["action"] = action
        return "Done — sent reactivation emails to 5 customer(s)."

    monkeypatch.setattr(svc.bot_actions, "execute_action", fake_exec)

    reply = svc.handle_inbound(INBOUND, "SIM", now=NOW)

    assert reply == "Done — sent reactivation emails to 5 customer(s)."
    assert seen["tenant_id"] == "t-1"
    assert seen["action"] == {"tool": "send_reactivation"}
    assert db.links[PHONE]["pending_action"] is None  # cleared


def test_confirm_no_cancels(db: FakeWhatsappDB) -> None:
    _verified_with_pending(db, {"tool": "send_reactivation"})
    reply = svc.handle_inbound(INBOUND, "não", now=NOW)
    assert "cancel" in reply.lower()
    assert db.links[PHONE]["pending_action"] is None


def test_random_text_clears_pending_and_falls_through(
    db: FakeWhatsappDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    _verified_with_pending(db, {"tool": "send_reactivation"})
    monkeypatch.setattr(svc.anthropic_client, "is_configured", lambda: True)
    monkeypatch.setattr(tenants_db, "get_by_id", lambda tid: {"name": "ACME"})
    monkeypatch.setattr(svc.anthropic_client, "run_conversation", lambda **kw: "CHAT")

    reply = svc.handle_inbound(INBOUND, "what about peak times?", now=NOW)

    assert reply == "CHAT"
    assert db.links[PHONE]["pending_action"] is None  # stale pending discarded


def test_expired_pending_is_not_executed(
    db: FakeWhatsappDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    _verified_with_pending(db, {"tool": "send_reactivation"}, expires_in_min=-1)
    executed: list[int] = []
    monkeypatch.setattr(
        svc.bot_actions, "execute_action", lambda *a, **k: executed.append(1) or "X"
    )
    monkeypatch.setattr(svc.anthropic_client, "is_configured", lambda: True)
    monkeypatch.setattr(tenants_db, "get_by_id", lambda tid: {"name": "ACME"})
    monkeypatch.setattr(svc.anthropic_client, "run_conversation", lambda **kw: "CHAT")

    reply = svc.handle_inbound(INBOUND, "SIM", now=NOW)

    # Expired pending → a stale "SIM" must NOT fire the action; treated as chat.
    assert executed == []
    assert reply == "CHAT"
