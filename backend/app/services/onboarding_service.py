import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.db import tenant_members, tenants

log = structlog.get_logger(__name__)

Row = dict[str, Any]

TRIAL_DAYS = 30


@dataclass
class BootstrapResult:
    tenant: Row
    is_new: bool


def _slug_from_email(email: str | None) -> str:
    if not email:
        return "owner"
    local = email.split("@")[0]
    cleaned = re.sub(r"[^a-z0-9-]+", "-", local.lower()).strip("-")
    return cleaned or "owner"


def _unique_slug(base: str) -> str:
    if tenants.get_by_slug(base) is None:
        return base
    for _ in range(8):
        candidate = f"{base}-{secrets.token_hex(2)}"
        if tenants.get_by_slug(candidate) is None:
            return candidate
    raise RuntimeError("could not generate unique slug")


def bootstrap_owner(
    *,
    user_id: str,
    email: str | None,
    business_name: str | None = None,
) -> BootstrapResult:
    existing_members = tenant_members.list_for_user(user_id)
    if existing_members:
        tenant = tenants.get_by_id(existing_members[0]["tenant_id"])
        if tenant is None:
            raise RuntimeError("tenant_member points to missing tenant")
        log.info("bootstrap_existing", user_id=user_id, tenant_id=tenant["id"])
        return BootstrapResult(tenant=tenant, is_new=False)

    slug = _unique_slug(_slug_from_email(email))
    trial_ends = datetime.now(UTC) + timedelta(days=TRIAL_DAYS)

    tenant = tenants.create(
        {
            "slug": slug,
            "name": business_name or "My business",
            "business_type": "other",
            "plan": "trial",
            "trial_ends_at": trial_ends.isoformat(),
        }
    )
    tenant_members.create(tenant_id=tenant["id"], user_id=user_id, role="owner")
    log.info("bootstrap_created", user_id=user_id, tenant_id=tenant["id"], slug=slug)
    return BootstrapResult(tenant=tenant, is_new=True)
