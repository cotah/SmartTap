from pydantic import BaseModel, Field


class ValidateRewardIn(BaseModel):
    validation_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ValidateRewardOut(BaseModel):
    reward_id: str
    redeemed_at: str
    description: str
    customer_id: str
    customer_name: str | None
