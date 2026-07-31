"""Per-tenant feature modules (tenants.enabled_modules, migration 018).

SmartTap sells one service by default (Google review replies); loyalty stays
in the codebase but is switched off per tenant. Public loyalty endpoints call
require_module so a reviews-only tenant exposes no loyalty surface at all.
"""

from typing import Any

from app.errors import NotFoundError

# Pre-migration rows (and older mocks) have no enabled_modules key — they keep
# the historical behavior of everything on. Matches the default in me.py.
DEFAULT_MODULES = ["loyalty", "reviews"]


def require_module(tenant: dict[str, Any], module: str) -> None:
    """Raise NotFoundError when `module` is not enabled for this tenant.

    404 (not 403) on purpose: a switched-off module should look like it
    doesn't exist rather than advertise that it's disabled.
    """
    enabled = tenant.get("enabled_modules") or DEFAULT_MODULES
    if module not in enabled:
        raise NotFoundError("Not found")
