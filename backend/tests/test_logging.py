"""Tests for the structlog output format.

Railway parses JSON log lines into structured attributes and displays the
`message` field — structlog's default `event` key made every app log line
render as a blank line in the Railway log viewer.
"""

import json

import pytest
import structlog

from app.main import _configure_logging


def test_structlog_events_render_with_message_key(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_logging("INFO")
    structlog.get_logger("test").info("hello_event", foo="bar")

    line = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["message"] == "hello_event"
    assert "event" not in payload
    assert payload["foo"] == "bar"
