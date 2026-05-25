"""Trial state computation for tenants.

Single source of truth for "is this tenant allowed to mutate their dashboard?"
The webhook handlers keep DB columns up to date (`plan`, `is_active`,
`trial_ends_at`); this module derives the user-facing status from those.

Read-only computation: no side effects, no DB writes. The dependency layer
calls into here to decide whether to raise a 402 on mutation routes.
"""

from datetime import UTC, datetime
from typing import Any, Literal

TrialStatus = Literal["active", "expiring_soon", "expired", "subscribed", "inactive"]

# How many days before trial_ends_at we start nudging the user to upgrade.
# Surfaced via API; the frontend banner uses this for the amber → red gradient.
EXPIRING_SOON_DAYS = 7


def _parse_iso(value: Any) -> datetime | None:
    """Tolerate timestamps that come back from Supabase with or without TZ.

    Supabase returns ISO-8601 with `+00:00`; that's fine for fromisoformat.
    Tests/fixtures sometimes pass naive datetimes — coerce those to UTC so
    downstream comparisons stay safe.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def compute_trial_status(tenant: dict[str, Any], *, now: datetime | None = None) -> TrialStatus:
    """Derive the trial state from a tenant row.

    Cases, in order:
        - is_active=False  → "inactive"        (canceled subscription; blocks edits)
        - plan != "trial"  → "subscribed"      (paid customer; no enforcement)
        - no trial_ends_at → "active"          (defensive: don't lock anyone out)
        - past trial_ends_at → "expired"       (blocks edits)
        - within EXPIRING_SOON_DAYS → "expiring_soon" (amber banner, still editable)
        - else → "active"
    """
    if not tenant.get("is_active", True):
        return "inactive"

    plan = tenant.get("plan")
    if plan and plan != "trial":
        return "subscribed"

    ends = _parse_iso(tenant.get("trial_ends_at"))
    if ends is None:
        # Defensive: an old tenant predating trial_ends_at, or a partial row.
        # Better to let them in than lock them out without explanation.
        return "active"

    current = now or datetime.now(UTC)
    if current >= ends:
        return "expired"

    days_left = (ends - current).total_seconds() / 86_400
    if days_left <= EXPIRING_SOON_DAYS:
        return "expiring_soon"
    return "active"


def is_blocking(status: TrialStatus) -> bool:
    """Status values that should reject mutations with a 402."""
    return status in ("expired", "inactive")
