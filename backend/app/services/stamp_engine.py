import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# Bounds for the configurable double_stamp multiplier. Lower bound is 2
# (1x would defeat the purpose); upper bound caps abuse and keeps reward
# pacing sane — a 10x campaign would burn through a 10-stamp card in one
# visit, which usually isn't what the owner intends.
MIN_MULTIPLIER = 2
MAX_MULTIPLIER = 5


@dataclass(frozen=True)
class RewardState:
    current_stamps: int
    stamps_for_reward: int
    stamps_remaining: int
    reward_ready: bool
    progress_percent: int


def can_award_stamp(
    last_stamp_at: datetime | None,
    rate_limit_minutes: int,
    now: datetime,
) -> bool:
    if last_stamp_at is None:
        return True
    if rate_limit_minutes <= 0:
        return True
    elapsed = (now - last_stamp_at).total_seconds() / 60
    return elapsed >= rate_limit_minutes


def compute_reward_state(current_stamps: int, stamps_for_reward: int) -> RewardState:
    if stamps_for_reward <= 0:
        return RewardState(0, stamps_for_reward, 0, False, 0)
    stamps_remaining = max(0, stamps_for_reward - current_stamps)
    reward_ready = current_stamps >= stamps_for_reward
    progress_percent = min(100, round((current_stamps / stamps_for_reward) * 100))
    return RewardState(
        current_stamps=current_stamps,
        stamps_for_reward=stamps_for_reward,
        stamps_remaining=stamps_remaining,
        reward_ready=reward_ready,
        progress_percent=progress_percent,
    )


def generate_validation_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def reward_expiry(now: datetime, days: int) -> datetime:
    return now + timedelta(days=days)


def multiplier_for_campaign(campaign: dict[str, Any] | None) -> int:
    """How many stamps to award per tap given the (possibly None) active campaign.

    None / non-double_stamp / malformed config → 1 (default behaviour).
    Valid double_stamp → clamp config.multiplier to [MIN_MULTIPLIER, MAX_MULTIPLIER].

    Clamping (rather than raising) keeps the tap path resilient: a corrupted
    config in one campaign must never prevent customers from earning stamps.
    """
    if campaign is None:
        return 1
    if campaign.get("type") != "double_stamp":
        return 1
    config = campaign.get("config") or {}
    raw = config.get("multiplier") if isinstance(config, dict) else None
    if raw is None:
        return MIN_MULTIPLIER
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return MIN_MULTIPLIER  # safest fallback for a double_stamp without a number
    if value < MIN_MULTIPLIER:
        return MIN_MULTIPLIER
    if value > MAX_MULTIPLIER:
        return MAX_MULTIPLIER
    return value
