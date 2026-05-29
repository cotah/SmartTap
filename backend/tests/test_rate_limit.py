"""Tests for the in-memory rate limiter (S5 audit S1).

Unit-level: the sliding window allows up to `limit` hits then blocks, and a
later window frees up again. The FastAPI dependency raises RateLimitError (429)
once the limit is hit.
"""

from typing import ClassVar

import pytest

from app.errors import RateLimitError
from app.services import rate_limit


def setup_function() -> None:
    rate_limit.reset()


def test_allows_up_to_limit_then_blocks() -> None:
    # 3 allowed within the window, 4th blocked.
    assert rate_limit.check("k", limit=3, window_seconds=60, now=100.0) is True
    assert rate_limit.check("k", limit=3, window_seconds=60, now=100.1) is True
    assert rate_limit.check("k", limit=3, window_seconds=60, now=100.2) is True
    assert rate_limit.check("k", limit=3, window_seconds=60, now=100.3) is False


def test_window_slides_and_frees_up() -> None:
    assert rate_limit.check("k", limit=1, window_seconds=10, now=0.0) is True
    assert rate_limit.check("k", limit=1, window_seconds=10, now=5.0) is False
    # After the window passes, the old hit drops off.
    assert rate_limit.check("k", limit=1, window_seconds=10, now=11.0) is True


def test_keys_are_independent() -> None:
    assert rate_limit.check("a", limit=1, window_seconds=60, now=0.0) is True
    assert rate_limit.check("b", limit=1, window_seconds=60, now=0.0) is True
    assert rate_limit.check("a", limit=1, window_seconds=60, now=0.1) is False


def test_dependency_raises_after_limit() -> None:
    dep = rate_limit.rate_limited("grp", limit=2, window_seconds=60)

    class FakeClient:
        host = "1.2.3.4"

    class FakeRequest:
        client = FakeClient()
        headers: ClassVar[dict[str, str]] = {}

    req = FakeRequest()
    dep(req)  # 1
    dep(req)  # 2
    with pytest.raises(RateLimitError):
        dep(req)  # 3 -> blocked
