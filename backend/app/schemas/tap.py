from typing import Literal

from pydantic import BaseModel, Field


class TapEventIn(BaseModel):
    magic_link_token: str | None = None
    device_type: Literal["ios", "android", "other", "unknown"] = "unknown"
    interaction_type: Literal["nfc", "qr"] = "nfc"


class TenantPublic(BaseModel):
    id: str
    slug: str
    name: str
    logo_url: str | None = None
    primary_color: str
    accent_color: str
    reward_description: str | None = None
    google_review_url: str | None = None


class CustomerSnapshot(BaseModel):
    id: str
    name: str | None = None
    current_stamps: int = Field(ge=0)


class RewardStateSnapshot(BaseModel):
    current_stamps: int = Field(ge=0)
    stamps_for_reward: int = Field(ge=0)
    stamps_remaining: int = Field(ge=0)
    reward_ready: bool
    progress_percent: int = Field(ge=0, le=100)


class RewardAvailable(BaseModel):
    id: str
    validation_code: str
    description: str
    expires_at: str


class ActiveCampaign(BaseModel):
    """The double_stamp campaign live at the moment of the tap, if any.
    Fed to the customer-facing page so it can render a "{multiplier}x today"
    badge — purely UI signal, not authoritative state."""

    id: str
    name: str
    multiplier: int = Field(ge=2, le=5)
    ends_at: str


class TapResponse(BaseModel):
    tenant: TenantPublic
    customer: CustomerSnapshot | None = None
    tap_id: str
    stamp_awarded: bool
    stamps_current: int = Field(ge=0)
    reward_state: RewardStateSnapshot
    reward_available: RewardAvailable | None = None
    active_campaign: ActiveCampaign | None = None
    # Number of stamps awarded by this specific tap (0 when rate-limited,
    # 1 normally, 2..5 during a double_stamp window).
    stamps_awarded_count: int = Field(default=0, ge=0)
