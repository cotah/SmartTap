from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_current_tenant_id, get_current_user
from app.schemas.billing import CheckoutSessionIn, CheckoutSessionOut
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
