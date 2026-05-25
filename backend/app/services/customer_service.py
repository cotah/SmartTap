from dataclasses import dataclass
from datetime import date
from typing import Any

import structlog

from app.db import customers, tenants
from app.db.customers import FilterMode, SortMode
from app.errors import InactiveError, NotFoundError

log = structlog.get_logger(__name__)

Row = dict[str, Any]


@dataclass(frozen=True)
class IdentifyContext:
    tenant_id: str
    phone: str
    name: str | None
    birthday: date | None
    gdpr_consent: bool
    gdpr_consent_text: str


@dataclass
class IdentifyResult:
    customer_id: str
    magic_link_token: str
    stamps_current: int
    is_new: bool


def identify_customer(ctx: IdentifyContext) -> IdentifyResult:
    tenant = tenants.get_by_id(ctx.tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": ctx.tenant_id})
    if not tenant["is_active"]:
        raise InactiveError("Tenant is no longer active")

    existing = customers.get_by_phone(ctx.tenant_id, ctx.phone)
    if existing is not None:
        log.info("customer_identified_existing", customer_id=existing["id"])
        return IdentifyResult(
            customer_id=existing["id"],
            magic_link_token=existing["magic_link_token"],
            stamps_current=existing["current_stamps"],
            is_new=False,
        )

    created = customers.create(
        tenant_id=ctx.tenant_id,
        phone=ctx.phone,
        name=ctx.name,
        birthday=ctx.birthday.isoformat() if ctx.birthday else None,
        gdpr_consent=ctx.gdpr_consent,
        gdpr_consent_text=ctx.gdpr_consent_text,
    )
    log.info("customer_created", customer_id=created["id"], tenant_id=ctx.tenant_id)
    return IdentifyResult(
        customer_id=created["id"],
        magic_link_token=created["magic_link_token"],
        stamps_current=0,
        is_new=True,
    )


@dataclass(frozen=True)
class ListCustomersContext:
    tenant_id: str
    search: str | None
    filter_mode: FilterMode
    sort: SortMode
    page: int
    limit: int


@dataclass(frozen=True)
class CustomerListRow:
    id: str
    name: str | None
    phone: str | None
    current_stamps: int
    total_visits: int
    last_visit_at: str | None
    created_at: str
    has_reward_ready: bool


@dataclass(frozen=True)
class CustomerListPage:
    items: list[CustomerListRow]
    total: int
    page: int
    limit: int


def list_customers(ctx: ListCustomersContext) -> CustomerListPage:
    tenant = tenants.get_by_id(ctx.tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": ctx.tenant_id})
    stamps_for_reward = int(tenant.get("stamps_for_reward") or 0)

    rows, total = customers.list_for_tenant(
        tenant_id=ctx.tenant_id,
        search=ctx.search,
        filter_mode=ctx.filter_mode,
        sort=ctx.sort,
        page=ctx.page,
        limit=ctx.limit,
        stamps_for_reward=stamps_for_reward,
    )

    items: list[CustomerListRow] = []
    for r in rows:
        current = int(r.get("current_stamps") or 0)
        items.append(
            CustomerListRow(
                id=r["id"],
                name=r.get("name"),
                phone=r.get("phone"),
                current_stamps=current,
                total_visits=int(r.get("total_visits") or 0),
                last_visit_at=r.get("last_visit_at"),
                created_at=r["created_at"],
                has_reward_ready=stamps_for_reward > 0 and current >= stamps_for_reward,
            )
        )
    return CustomerListPage(items=items, total=total, page=ctx.page, limit=ctx.limit)


EXPORT_MAX_ROWS = 10_000


@dataclass(frozen=True)
class ExportCustomersContext:
    tenant_id: str
    search: str | None
    filter_mode: FilterMode
    sort: SortMode


def export_customers_csv(ctx: ExportCustomersContext) -> str:
    """Returns up to EXPORT_MAX_ROWS customers as a CSV string.

    Reuses list_customers paginated under the hood so filtering stays consistent
    with the dashboard view. Cap prevents accidental megabyte downloads for
    tenants that grow far beyond MVP assumptions.
    """
    import csv
    import io

    tenant = tenants.get_by_id(ctx.tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": ctx.tenant_id})
    stamps_for_reward = int(tenant.get("stamps_for_reward") or 0)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "name",
            "phone",
            "current_stamps",
            "total_visits",
            "last_visit_at",
            "created_at",
            "has_reward_ready",
        ]
    )

    page_size = 500
    written = 0
    page = 1
    while written < EXPORT_MAX_ROWS:
        rows, total = customers.list_for_tenant(
            tenant_id=ctx.tenant_id,
            search=ctx.search,
            filter_mode=ctx.filter_mode,
            sort=ctx.sort,
            page=page,
            limit=page_size,
            stamps_for_reward=stamps_for_reward,
        )
        if not rows:
            break
        for r in rows:
            if written >= EXPORT_MAX_ROWS:
                break
            current = int(r.get("current_stamps") or 0)
            ready = stamps_for_reward > 0 and current >= stamps_for_reward
            writer.writerow(
                [
                    r["id"],
                    r.get("name") or "",
                    r.get("phone") or "",
                    current,
                    int(r.get("total_visits") or 0),
                    r.get("last_visit_at") or "",
                    r["created_at"],
                    "yes" if ready else "no",
                ]
            )
            written += 1
        if page * page_size >= total:
            break
        page += 1

    return buf.getvalue()
