"""Dashboard-facing report endpoints.

For S4-W3 there is exactly one endpoint: download the monthly PDF on demand.
The same computation + renderer that the cron uses, executed live for the
authenticated tenant. Nothing is persisted — generation is cheap (sub-second
for a typical month) and storing files would mean an extra bucket and a
clean-up policy we don't need.

Period defaults to the previous complete Dublin month, matching the cron.
Callers can pass `year` and `month` to inspect any past month (the report
gracefully renders empty months as goose-eggs).
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.dependencies import get_current_tenant_id
from app.errors import NotFoundError
from app.services import monthly_report_service, pdf_renderer

router = APIRouter(tags=["reports"])
log = structlog.get_logger(__name__)


def _resolve_period(year: int | None, month: int | None) -> tuple[int, int]:
    """Both-or-none — partial overrides would be ambiguous. With both unset,
    default to the previous complete Dublin month (matches the cron contract)."""
    if (year is None) != (month is None):
        raise HTTPException(
            status_code=400,
            detail="year and month must be provided together",
        )
    if year is None or month is None:
        return monthly_report_service.resolve_previous_complete_month()
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    # Year guard prevents accidental 4-digit overflow in URLs (the request
    # would otherwise hit Postgres with "year out of range" much later).
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="year out of range")
    return year, month


@router.get("/reports/monthly.pdf")
def download_monthly_report(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
) -> Response:
    """Stream the PDF directly. Content-Disposition: attachment so browsers
    save instead of trying to render inline (saves the merchant the extra
    click on iOS Safari especially)."""
    target_year, target_month = _resolve_period(year, month)

    try:
        report = monthly_report_service.compute(
            tenant_id=tenant_id, year=target_year, month=target_month
        )
    except NotFoundError as exc:
        # Translate the service-layer NotFound into a clean 404. Same shape
        # as other routes that route through dependencies — the global
        # BusinessError handler would do this for us if NotFoundError
        # inherited from BusinessError, but reports don't need the structured
        # error body so the explicit raise is clearer.
        raise HTTPException(status_code=404, detail="Tenant not found") from exc

    pdf_bytes = pdf_renderer.render_monthly_report(report)
    filename = pdf_renderer.report_filename(report)

    log.info(
        "monthly_report_downloaded",
        tenant_id=tenant_id,
        year=target_year,
        month=target_month,
        bytes=len(pdf_bytes),
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # PDF is computed fresh each call; tell intermediaries not to
            # cache (could leak across tenants on a misconfigured proxy).
            "Cache-Control": "private, no-store",
        },
    )
