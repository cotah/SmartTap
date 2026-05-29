"""Tests for the Anthropic tool-use loop (S5 Feature 1, Phase A).

A fake Anthropic client drives the loop through its branches: tool_use ->
dispatch -> final text, the iteration cap, and per-tool error isolation. No
real API calls.
"""

from types import SimpleNamespace
from typing import Any, ClassVar

import pytest

from app.services import anthropic_client


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_block(tool_id: str, name: str, tool_input: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=tool_input)


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
    # run_conversation does `from anthropic import Anthropic` at call time, so
    # patching the attribute on the real module is enough.
    monkeypatch.setattr("anthropic.Anthropic", FakeAnthropic)


def test_tool_use_then_final_text() -> None:
    FakeAnthropic.queued = [
        _resp("tool_use", [_tool_block("tu_1", "get_overview", {})]),
        _resp("end_turn", [_text_block("You have 42 customers.")]),
    ]
    dispatched: list[tuple[str, dict[str, Any]]] = []

    def dispatch(name: str, tool_input: dict[str, Any]) -> str:
        dispatched.append((name, tool_input))
        return '{"customers_total": 42}'

    out = anthropic_client.run_conversation(
        system="sys",
        user_text="how many customers?",
        tools=[{"name": "get_overview"}],
        dispatch=dispatch,
    )

    assert out == "You have 42 customers."
    assert dispatched == [("get_overview", {})]


def test_iteration_cap_returns_fallback() -> None:
    # Always asks for a tool — never finishes. Loop must bail after the cap.
    FakeAnthropic.queued = [
        _resp("tool_use", [_tool_block(f"tu_{i}", "get_overview", {})]) for i in range(10)
    ]

    out = anthropic_client.run_conversation(
        system="sys",
        user_text="loop forever",
        tools=[{"name": "get_overview"}],
        dispatch=lambda n, i: "{}",
        max_iterations=3,
    )

    assert "couldn't" in out.lower()


def test_tool_error_is_isolated_and_loop_continues() -> None:
    FakeAnthropic.queued = [
        _resp("tool_use", [_tool_block("tu_1", "boom", {})]),
        _resp("end_turn", [_text_block("Handled gracefully.")]),
    ]

    def dispatch(name: str, tool_input: dict[str, Any]) -> str:
        raise RuntimeError("tool blew up")

    out = anthropic_client.run_conversation(
        system="sys", user_text="x", tools=[{"name": "boom"}], dispatch=dispatch
    )

    assert out == "Handled gracefully."
    # The error turn fed an is_error tool_result back to Claude.
    inst = FakeAnthropic.last_instance
    assert inst is not None
    second_call_messages = inst.messages.calls[1]["messages"]
    tool_result = second_call_messages[-1]["content"][0]
    assert tool_result["is_error"] is True


def test_unconfigured_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(anthropic_client, "is_configured", lambda: False)
    with pytest.raises(RuntimeError):
        anthropic_client.run_conversation(
            system="s", user_text="u", tools=[], dispatch=lambda n, i: ""
        )


# ---------------------------------------------------------------------------
# generate_text (single-shot, used by Feature 3)
# ---------------------------------------------------------------------------


def test_generate_text_returns_reply() -> None:
    FakeAnthropic.queued = [_resp("end_turn", [_text_block("Thanks for visiting!")])]
    out = anthropic_client.generate_text(system="reply as owner", user_text="5-star review")
    assert out == "Thanks for visiting!"


def test_generate_text_unconfigured_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(anthropic_client, "is_configured", lambda: False)
    with pytest.raises(RuntimeError):
        anthropic_client.generate_text(system="s", user_text="u")
