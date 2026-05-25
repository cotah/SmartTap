from typing import Literal

from pydantic import BaseModel, Field

BusinessType = Literal["barbershop", "cafe", "pet_grooming", "salon", "tattoo", "other"]


class OnboardingCompleteIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=80)
    business_type: BusinessType
    google_review_url: str | None = Field(default=None, max_length=500)
    stamps_for_reward: int = Field(ge=1, le=50)
    reward_description: str = Field(min_length=2, max_length=120)
    reward_expires_days: int = Field(ge=1, le=365)
    stamp_rate_limit_minutes: int = Field(ge=0, le=1440)
