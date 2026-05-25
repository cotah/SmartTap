from dataclasses import dataclass
from datetime import date
from typing import Any

import structlog

from app.db import customers, tenants
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
