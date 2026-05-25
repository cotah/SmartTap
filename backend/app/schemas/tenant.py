from typing import Literal

from pydantic import BaseModel, Field

HexColor = str


class TenantSettingsUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    logo_url: str | None = None
    primary_color: HexColor | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: HexColor | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    google_place_id: str | None = None
    google_review_url: str | None = None
    google_business_url: str | None = None


class RewardConfigIn(BaseModel):
    stamps_for_reward: int = Field(ge=1, le=50)
    reward_description: str = Field(min_length=2, max_length=120)
    reward_expires_days: int = Field(ge=1, le=365)
    stamp_rate_limit_minutes: int = Field(ge=0, le=1440)


BusinessType = Literal["barbershop", "cafe", "pet_grooming", "salon", "tattoo", "other"]
