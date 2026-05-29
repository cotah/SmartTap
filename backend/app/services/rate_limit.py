"""Lightweight in-memory rate limiter (S5 audit — S1).

A per-process sliding-window counter used to protect a few abuse-sensitive
PUBLIC endpoints (reward-code validation = brute-force target; customer
identify = enumeration). Authenticated dashboard endpoints rely on auth +
tenant scoping; high-volume legitimate endpoints (taps) are intentionally NOT
limited here to avoid false positives on shared café IPs — those are protected
at the edge (Cloudflare).

LIMITATION (documented on purpose): state is per-process, so with multiple
Railway replicas the effective limit is per-replica, and it resets on deploy.
This is a meaningful first layer, not a distributed guarantee. For hard limits,
move the window to Redis/Upstash. Tracked as a follow-up.
"""

import time
from collections.abc import Callable

import structlog
from fastapi import Request

from app.errors import RateLimitError

log = structlog.get_logger(__name__)

# key -> list of hit timestamps (monotonic seconds) within the current window.
_hits: dict[str, list[float]] = {}
# Safety cap so a flood of distinct keys (IPs) can't grow the dict unbounded.
_MAX_KEYS = 50_000


def reset() -> None:
    """Clear all state — used by tests."""
    _hits.clear()


def check(key: str, *, limit: int, window_seconds: float, now: float | None = None) -> bool:
    """Return True if this hit is allowed, False if it exceeds `limit` within
    the trailing `window_seconds`. Records the hit when allowed."""
    current = now if now is not None else time.monotonic()
    cutoff = current - window_seconds

    bucket = _hits.get(key)
    if bucket is None:
        if len(_hits) >= _MAX_KEYS:
            # Pathological key churn — drop the whole map rather than leak.
            _hits.clear()
        bucket = []
        _hits[key] = bucket

    # Drop timestamps outside the window.
    bucket[:] = [t for t in bucket if t > cutoff]
    if len(bucket) >= limit:
        return False
    bucket.append(current)
    return True


def _client_ip(request: Request) -> str:
    """Best-effort client IP. Behind Railway/Cloudflare the real IP is in
    X-Forwarded-For (first hop); fall back to the socket peer."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limited(group: str, *, limit: int, window_seconds: float) -> Callable[[Request], None]:
    """FastAPI dependency factory. Raises RateLimitError (429) when the caller
    exceeds `limit` requests to `group` within `window_seconds`."""

    def dependency(request: Request) -> None:
        key = f"{group}:{_client_ip(request)}"
        if not check(key, limit=limit, window_seconds=window_seconds):
            log.info("rate_limited", group=group)
            raise RateLimitError("Too many requests. Please slow down and try again shortly.")

    return dependency
