from typing import Annotated

from fastapi import APIRouter, Depends

from app.db import tenant_members, tenants
from app.dependencies import CurrentUser, get_current_user
from app.schemas.me import BootstrapIn, BootstrapResponse, MeResponse, TenantSummary
from app.services.onboarding_service import bootstrap_owner
from app.services.trial_service import compute_trial_status

router = APIRouter(tags=["me"])


def _summary(tenant: dict) -> TenantSummary:  # type: ignore[type-arg]
    return TenantSummary(
        id=tenant["id"],
        slug=tenant["slug"],
        name=tenant["name"],
        business_type=tenant["business_type"],
        plan=tenant["plan"],
        is_active=tenant["is_active"],
        trial_ends_at=tenant.get("trial_ends_at"),
        onboarding_complete=bool(tenant.get("reward_description")),
        trial_status=compute_trial_status(tenant),
    )


@router.get("/me", response_model=MeResponse)
def get_me(user: Annotated[CurrentUser, Depends(get_current_user)]) -> MeResponse:
    members = tenant_members.list_for_user(user.user_id)
    summary: TenantSummary | None = None
    if members:
        tenant = tenants.get_by_id(members[0]["tenant_id"])
        if tenant is not None:
            summary = _summary(tenant)
    return MeResponse(user_id=user.user_id, email=user.email, tenant=summary)


@router.post("/me/bootstrap", response_model=BootstrapResponse)
def bootstrap_me(
    body: BootstrapIn,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> BootstrapResponse:
    result = bootstrap_owner(
        user_id=user.user_id,
        email=user.email,
        business_name=body.business_name,
    )
    return BootstrapResponse(tenant=_summary(result.tenant), is_new=result.is_new)
