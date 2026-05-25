from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

BillingPlan = Literal["review", "loyalty", "pro", "network"]


class CheckoutSessionIn(BaseModel):
    plan: BillingPlan
    success_url: HttpUrl
    cancel_url: HttpUrl


class CheckoutSessionOut(BaseModel):
    url: str = Field(min_length=1)
