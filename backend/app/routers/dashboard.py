from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_tenant_id
from app.schemas.dashboard import DashboardOverview
from app.services.dashboard_service import overview as compute_overview

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/overview", response_model=DashboardOverview)
def get_overview(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> DashboardOverview:
    m = compute_overview(tenant_id)
    return DashboardOverview(
        customers_total=m.customers_total,
        taps_week=m.taps_week,
        reviews_month=m.reviews_month,
        customers_at_risk=m.customers_at_risk,
        active_stamps_total=m.active_stamps_total,
    )
