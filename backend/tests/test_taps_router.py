"""Router-level wiring for the post-visit thank-you.

The thank-you policy lives in visit_thankyou_service (tested separately). Here
we only assert the router schedules that work as a BackgroundTask — after the
response, only when a stamp was earned for an identified customer — and skips
scheduling on the common anonymous / no-stamp taps.
"""

from typing import Any

import pytest
from fastapi import BackgroundTasks

from app.routers import taps as router
from app.schemas.tap import TapEventIn
from app.services.tap_service import TapResult


class _FakeRequest:
    """Minimal stand-in for starlette Request — only the bits register_tap reads."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {"user-agent": "pytest"}

        class _Client:
            host = "1.2.3.4"

        self.client = _Client()


def _tenant() -> dict[str, Any]:
    return {
        "id": "t-1",
        "slug": "acme",
        "name": "ACME Barber",
        "logo_url": None,
        "primary_color": "#000000",
        "accent_color": "#00D4FF",
        "reward_description": "a free cut",
        "google_review_url": "https://g.page/r/acme",
        "stamps_for_reward": 10,
    }


def _customer() -> dict[str, Any]:
    return {"id": "c-1", "name": "Alex", "current_stamps": 4}


def _result(*, stamp_awarded: bool, customer: dict[str, Any] | None) -> TapResult:
    return TapResult(
        tenant=_tenant(),
        customer=customer,
        stamps_current=customer["current_stamps"] if customer else 0,
        reward_available=None,
        tap_id="tap-1",
        stamp_awarded=stamp_awarded,
        active_campaign=None,
        stamps_awarded_count=1 if stamp_awarded else 0,
    )


def _body() -> TapEventIn:
    return TapEventIn(device_type="ios", interaction_type="nfc", magic_link_token="mlt-1")


def test_schedules_thankyou_when_stamp_awarded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router, "process_tap", lambda _ctx: _result(stamp_awarded=True, customer=_customer())
    )
    bg = BackgroundTasks()

    router.register_tap("abc", _body(), _FakeRequest(), bg)  # type: ignore[arg-type]

    assert len(bg.tasks) == 1
    task = bg.tasks[0]
    assert task.func is router.visit_thankyou_service.maybe_send
    assert task.kwargs["tenant"]["id"] == "t-1"
    assert task.kwargs["customer"]["id"] == "c-1"
    assert task.kwargs["stamp_awarded"] is True


def test_no_thankyou_when_no_stamp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router, "process_tap", lambda _ctx: _result(stamp_awarded=False, customer=_customer())
    )
    bg = BackgroundTasks()

    router.register_tap("abc", _body(), _FakeRequest(), bg)  # type: ignore[arg-type]

    assert bg.tasks == []


def test_no_thankyou_for_anonymous_tap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        router, "process_tap", lambda _ctx: _result(stamp_awarded=True, customer=None)
    )
    bg = BackgroundTasks()

    router.register_tap("abc", _body(), _FakeRequest(), bg)  # type: ignore[arg-type]

    assert bg.tasks == []
