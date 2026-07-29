from typing import Annotated

from fastapi import APIRouter, Depends, Header

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
        enabled_modules=tenant.get("enabled_modules") or ["loyalty", "reviews"],
    )


@router.get("/me", response_model=MeResponse)
def get_me(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
) -> MeResponse:
    members = tenant_members.list_for_user(user.user_id)
    summaries: list[TenantSummary] = []
    for member in members:
        tenant = tenants.get_by_id(member["tenant_id"])
        if tenant is not None:
            summaries.append(_summary(tenant))
    # Active tenant: the X-Tenant-Id header when it names a membership,
    # otherwise the first membership (legacy behavior).
    summary: TenantSummary | None = None
    if summaries:
        summary = next((s for s in summaries if s.id == x_tenant_id), summaries[0])
    return MeResponse(
        user_id=user.user_id, email=user.email, tenant=summary, tenants=summaries
    )


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
