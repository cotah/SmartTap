from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

BillingPlan = Literal["review", "loyalty", "pro", "network"]
TenantPlan = Literal["trial", "review", "loyalty", "pro", "network"]


class CheckoutSessionIn(BaseModel):
    plan: BillingPlan
    success_url: HttpUrl
    cancel_url: HttpUrl


class CheckoutSessionOut(BaseModel):
    url: str = Field(min_length=1)


class PortalSessionIn(BaseModel):
    return_url: HttpUrl


class PortalSessionOut(BaseModel):
    url: str = Field(min_length=1)


TrialStatus = Literal["active", "expiring_soon", "expired", "subscribed", "inactive"]


class SubscriptionSummary(BaseModel):
    """What the dashboard needs to render the billing page.

    `has_subscription` is true once a checkout has completed (we own a Stripe
    subscription_id). Stripe-derived fields are only present then.
    """

    plan: TenantPlan
    is_active: bool
    is_founding_member: bool
    trial_ends_at: str | None
    cancelled_at: str | None
    has_subscription: bool
    # Filled from Stripe when has_subscription=True. Null when on trial or
    # when Stripe is temporarily unreachable (we still render the page).
    status: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool | None = None
    # Computed from plan + is_active + trial_ends_at; mirrors the value in
    # /me so the billing page can render banners without a second fetch.
    trial_status: TrialStatus = "active"
