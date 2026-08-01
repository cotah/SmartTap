"""Tests for the Anthropic client (S5 Feature 3).

A fake Anthropic client stands in for the SDK. No real API calls.
"""

from types import SimpleNamespace
from typing import Any, ClassVar

import pytest

from app.services import anthropic_client


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _resp(stop_reason: str, content: list[Any]) -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, content=content)


class FakeMessages:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeAnthropic:
    last_instance: ClassVar["FakeAnthropic | None"] = None
    queued: ClassVar[list[Any]] = []

    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key
        self.messages = FakeMessages(FakeAnthropic.queued)
        FakeAnthropic.last_instance = self


@pytest.fixture(autouse=True)
def _configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend the key is set and inject the fake SDK client."""
    monkeypatch.setattr(anthropic_client, "is_configured", lambda: True)

    class FakeSettings:
        anthropic_api_key = "sk-test"
        anthropic_model = "claude-sonnet-4-6"

    monkeypatch.setattr(anthropic_client, "get_settings", lambda: FakeSettings())
    # generate_text does `from anthropic import Anthropic` at call time, so
    # patching the attribute on the real module is enough.
    monkeypatch.setattr("anthropic.Anthropic", FakeAnthropic)


def test_generate_text_returns_reply() -> None:
    FakeAnthropic.queued = [_resp("end_turn", [_text_block("Thanks for visiting!")])]
    out = anthropic_client.generate_text(system="reply as owner", user_text="5-star review")
    assert out == "Thanks for visiting!"


def test_generate_text_unconfigured_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(anthropic_client, "is_configured", lambda: False)
    with pytest.raises(RuntimeError):
        anthropic_client.generate_text(system="s", user_text="u")
