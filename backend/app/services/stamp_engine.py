import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta


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
