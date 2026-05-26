"""Business rules for tenant campaigns.

S4-W1 scope: double_stamp campaigns. Other types (reactivation, birthday)
are accepted by the schema but not modelled here — they ship in later
sprints with their own validation rules.

Invariants enforced here, not in the DB:
    - Only one `double_stamp` campaign can be in `active` status per tenant
      at any time (even future-dated ones).
    - Multiplier is clamped to [MIN_MULTIPLIER, MAX_MULTIPLIER].
    - starts_at < ends_at.
    - Once a campaign is `active`, only its `status` can change (pause/end).
      All other fields require the campaign to be in `draft`.
"""

from datetime import UTC, datetime
from typing import Any, Literal

import structlog

from app.db import campaigns
from app.errors import BusinessError, NotFoundError
from app.services.stamp_engine import MAX_MULTIPLIER, MIN_MULTIPLIER

log = structlog.get_logger(__name__)

CampaignType = Literal["double_stamp", "reactivation", "birthday", "custom"]
CampaignStatus = Literal["draft", "active", "paused", "ended"]

Row = dict[str, Any]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class InvalidCampaignError(BusinessError):
    status_code = 422
    code = "invalid_campaign"


class ConflictingCampaignError(BusinessError):
    status_code = 409
    code = "conflicting_campaign"


class CampaignLockedError(BusinessError):
    status_code = 409
    code = "campaign_locked"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_window(starts_at: datetime, ends_at: datetime) -> None:
    if ends_at <= starts_at:
        raise InvalidCampaignError(
            "Campaign end must be after the start.",
            detail={"starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
        )


def _validate_multiplier(multiplier: int) -> None:
    if multiplier < MIN_MULTIPLIER or multiplier > MAX_MULTIPLIER:
        raise InvalidCampaignError(
            f"Multiplier must be between {MIN_MULTIPLIER} and {MAX_MULTIPLIER}.",
            detail={"multiplier": str(multiplier)},
        )


def _validate_name(name: str) -> None:
    cleaned = name.strip()
    if len(cleaned) < 2 or len(cleaned) > 80:
        raise InvalidCampaignError(
            "Campaign name must be between 2 and 80 characters.",
            detail={"name_length": str(len(cleaned))},
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_for_tenant(tenant_id: str) -> list[Row]:
    return campaigns.list_for_tenant(tenant_id)


def get_owned(tenant_id: str, campaign_id: str) -> Row:
    """Fetch a campaign and assert tenant ownership in one step. Returns the
    row; raises NotFoundError when missing OR cross-tenant."""
    row = campaigns.get_by_id(campaign_id)
    if row is None or row.get("tenant_id") != tenant_id:
        raise NotFoundError("Campaign not found", detail={"campaign_id": campaign_id})
    return row


def create_double_stamp(
    *,
    tenant_id: str,
    name: str,
    multiplier: int,
    starts_at: datetime,
    ends_at: datetime,
    status: CampaignStatus = "draft",
) -> Row:
    """Create a new double_stamp campaign. Defaults to `draft` so the owner
    can review before going live. Passing status='active' triggers the
    uniqueness check just like a later activation would."""
    _validate_name(name)
    _validate_multiplier(multiplier)
    _validate_window(starts_at, ends_at)

    if status == "active" and campaigns.has_other_active_double_stamp(tenant_id):
        raise ConflictingCampaignError(
            "Another double-stamp campaign is already active. Pause it first.",
            detail={"tenant_id": tenant_id},
        )

    row = campaigns.create(
        {
            "tenant_id": tenant_id,
            "name": name.strip(),
            "type": "double_stamp",
            "status": status,
            "config": {"multiplier": multiplier},
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
        }
    )
    log.info(
        "campaign_created",
        tenant_id=tenant_id,
        campaign_id=row["id"],
        status=status,
    )
    return row


def update_campaign(
    *,
    tenant_id: str,
    campaign_id: str,
    name: str | None = None,
    multiplier: int | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> Row:
    """Update fields on a `draft` campaign. Activating, pausing or ending
    a campaign goes through `change_status` instead — keep state machines
    visible at the call site."""
    row = get_owned(tenant_id, campaign_id)
    if row["status"] != "draft":
        raise CampaignLockedError(
            "Only draft campaigns can be edited. Pause to draft state first.",
            detail={"current_status": row["status"]},
        )

    fields: dict[str, Any] = {}
    if name is not None:
        _validate_name(name)
        fields["name"] = name.strip()
    if multiplier is not None:
        _validate_multiplier(multiplier)
        fields["config"] = {"multiplier": multiplier}

    new_starts = starts_at or _parse_iso(row.get("starts_at"))
    new_ends = ends_at or _parse_iso(row.get("ends_at"))
    if new_starts and new_ends:
        _validate_window(new_starts, new_ends)
    if starts_at is not None:
        fields["starts_at"] = starts_at.isoformat()
    if ends_at is not None:
        fields["ends_at"] = ends_at.isoformat()

    if not fields:
        return row  # nothing to do — return current state for consistency

    updated = campaigns.update(campaign_id, fields)
    log.info("campaign_updated", tenant_id=tenant_id, campaign_id=campaign_id)
    return updated


def change_status(
    *,
    tenant_id: str,
    campaign_id: str,
    new_status: CampaignStatus,
) -> Row:
    """Transition a campaign between draft / active / paused / ended.

    `active` is the only status that triggers the uniqueness check — multiple
    drafts or paused campaigns can coexist.
    """
    row = get_owned(tenant_id, campaign_id)
    current = row["status"]
    if current == new_status:
        return row

    # The "ended" state is terminal — re-activating an ended campaign would
    # confuse stamp accounting. Owner must clone into a new draft.
    if current == "ended":
        raise CampaignLockedError(
            "Ended campaigns can't be reactivated. Create a new one.",
            detail={"campaign_id": campaign_id},
        )

    if new_status == "active" and campaigns.has_other_active_double_stamp(
        tenant_id, excluding_id=campaign_id
    ):
        raise ConflictingCampaignError(
            "Another double-stamp campaign is already active. Pause it first.",
            detail={"tenant_id": tenant_id},
        )

    updated = campaigns.update(campaign_id, {"status": new_status})
    log.info(
        "campaign_status_changed",
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        from_status=current,
        to_status=new_status,
    )
    return updated


def find_active_for_tap(tenant_id: str, *, now: datetime | None = None) -> Row | None:
    """Thin wrapper around the DB lookup, used by tap_service. Kept here so
    tap_service depends on the service layer (testable) rather than the DB."""
    current = now or datetime.now(UTC)
    return campaigns.find_active_double_stamp(tenant_id, current)


def _parse_iso(value: Any) -> datetime | None:
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
