from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_tenant_id
from app.schemas.dashboard import DashboardOverview, TapPoint, TapsTimeseries
from app.services.dashboard_service import overview as compute_overview
from app.services.dashboard_service import taps_timeseries as compute_timeseries

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
        loyalty_visits_today=m.loyalty_visits_today,
    )


@router.get("/dashboard/taps-timeseries", response_model=TapsTimeseries)
def get_taps_timeseries(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> TapsTimeseries:
    points = compute_timeseries(tenant_id, days=days)
    return TapsTimeseries(
        points=[
            TapPoint(date=p.date, stamps=p.stamps, reviews=p.reviews) for p in points
        ]
    )
