from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_current_tenant_id, get_current_user
from app.schemas.billing import (
    CheckoutSessionIn,
    CheckoutSessionOut,
    PortalSessionIn,
    PortalSessionOut,
    SubscriptionSummary,
)
from app.services import billing_service

router = APIRouter(tags=["billing"])


@router.post("/billing/checkout-session", response_model=CheckoutSessionOut)
def create_checkout_session_endpoint(
    body: CheckoutSessionIn,
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CheckoutSessionOut:
    url = billing_service.create_checkout_session(
        tenant_id=tenant_id,
        plan=body.plan,
        email=user.email,
        success_url=str(body.success_url),
        cancel_url=str(body.cancel_url),
    )
    return CheckoutSessionOut(url=url)


@router.post("/billing/portal-session", response_model=PortalSessionOut)
def create_portal_session_endpoint(
    body: PortalSessionIn,
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> PortalSessionOut:
    url = billing_service.create_portal_session(
        tenant_id=tenant_id,
        return_url=str(body.return_url),
    )
    return PortalSessionOut(url=url)


@router.get("/billing/subscription", response_model=SubscriptionSummary)
def get_subscription_endpoint(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> SubscriptionSummary:
    return billing_service.get_subscription_summary(tenant_id)
