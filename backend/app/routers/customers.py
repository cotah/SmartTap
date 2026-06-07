from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import Response

from app.dependencies import get_current_tenant_id
from app.schemas.customer import (
    CustomerIdentifyIn,
    CustomerIdentifyOut,
    CustomerListItem,
    CustomerListResponse,
    CustomerStats,
)
from app.services import reactivation_service
from app.services.customer_service import (
    ExportCustomersContext,
    IdentifyContext,
    ListCustomersContext,
    customer_stats,
    export_customers_csv,
    identify_customer,
    list_customers,
)
from app.services.rate_limit import rate_limited

router = APIRouter(tags=["customers"])


@router.post("/customers/opt-out/{magic_link_token}", status_code=204)
def opt_out_customer(
    magic_link_token: Annotated[str, Path(min_length=8, max_length=128)],
) -> Response:
    """Public, one-click GDPR opt-out triggered from the email footer.

    Idempotent — clicking the link twice still returns 204. The router lets
    the service raise NotFoundError when the token doesn't match anything;
    the global handler turns that into a 404 without revealing whether the
    token was malformed or just unknown (prevents enumeration).

    Not protected by auth: the magic token IS the bearer. It's bound to a
    single customer row and only used here, so leak surface is the same as
    a one-time unsubscribe link.
    """
    reactivation_service.opt_out(magic_link_token)
    return Response(status_code=204)


_identify_rl = rate_limited("customer_identify", limit=20, window_seconds=60)


@router.post("/customers/identify", response_model=CustomerIdentifyOut)
def identify_customer_endpoint(
    body: CustomerIdentifyIn,
    _rl: Annotated[None, Depends(_identify_rl)] = None,
) -> CustomerIdentifyOut:
    # Public opt-in flow: tenant_id comes from the body (the tapped tag). Rate
    # limited per IP (S1) to curb mass customer-record pollution.
    ctx = IdentifyContext(
        tenant_id=body.tenant_id,
        phone=body.phone,
        name=body.name,
        email=body.email,
        birthday=body.birthday,
        gdpr_consent=body.gdpr_consent,
        gdpr_consent_text=body.gdpr_consent_text,
    )
    result = identify_customer(ctx)
    return CustomerIdentifyOut(
        customer_id=result.customer_id,
        magic_link_token=result.magic_link_token,
        stamps_current=result.stamps_current,
    )


@router.get("/customers/export.csv")
def export_customers_endpoint(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    search: Annotated[str | None, Query(max_length=80)] = None,
    filter: Annotated[
        Literal["all", "active", "at_risk", "has_reward"], Query()
    ] = "all",
    sort: Annotated[Literal["recent", "visits", "stamps"], Query()] = "recent",
) -> Response:
    csv_text = export_customers_csv(
        ExportCustomersContext(
            tenant_id=tenant_id,
            search=search.strip() if search else None,
            filter_mode=filter,
            sort=sort,
        )
    )
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="customers.csv"'},
    )


@router.get("/customers/stats", response_model=CustomerStats)
def customer_stats_endpoint(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> CustomerStats:
    """Counts for the four loyalty summary cards (total / active / at risk /
    reward ready), each matching the list its filter opens."""
    s = customer_stats(tenant_id)
    return CustomerStats(
        total=s.total,
        active=s.active,
        at_risk=s.at_risk,
        reward_ready=s.reward_ready,
    )


@router.get("/customers", response_model=CustomerListResponse)
def list_customers_endpoint(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    search: Annotated[str | None, Query(max_length=80)] = None,
    filter: Annotated[
        Literal["all", "active", "at_risk", "has_reward"], Query()
    ] = "all",
    sort: Annotated[Literal["recent", "visits", "stamps"], Query()] = "recent",
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CustomerListResponse:
    ctx = ListCustomersContext(
        tenant_id=tenant_id,
        search=search.strip() if search else None,
        filter_mode=filter,
        sort=sort,
        page=page,
        limit=limit,
    )
    result = list_customers(ctx)
    return CustomerListResponse(
        items=[
            CustomerListItem(
                id=row.id,
                name=row.name,
                phone=row.phone,
                current_stamps=row.current_stamps,
                total_visits=row.total_visits,
                last_visit_at=row.last_visit_at,  # type: ignore[arg-type]
                created_at=row.created_at,  # type: ignore[arg-type]
                has_reward_ready=row.has_reward_ready,
            )
            for row in result.items
        ],
        total=result.total,
        page=result.page,
        limit=result.limit,
    )
