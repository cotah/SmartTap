"""Write actions the WhatsApp bot can take (S5 Feature 1, Phase B).

Two kinds of action:
    - Confirmable (affect customers/data): send_reactivation, create_double_stamp.
      `handle_write_tool` does NOT execute them — it validates, builds a human
      summary, stores a pending action on the link, and returns a
      confirmation-needed message. `execute_action` runs them once the owner
      replies SIM.
    - Direct (owner-facing, low risk): send_monthly_report — runs immediately.

All confirmable actions respect the same trial gate as dashboard mutations.
Everything no-ops safely without external credentials (dev/CI).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.db import customers, whatsapp
from app.services import (
    campaign_service,
    monthly_report_service,
    pdf_renderer,
    reactivation_service,
    trial_service,
    whatsapp_client,
)

log = structlog.get_logger(__name__)

PENDING_TTL_MINUTES = 5
DEFAULT_MULTIPLIER = 2

WRITE_TOOL_NAMES = {"send_reactivation", "create_double_stamp", "send_monthly_report"}
# Actions that require explicit confirmation before they run.
CONFIRMABLE = {"send_reactivation", "create_double_stamp"}

WRITE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "send_reactivation",
        "description": (
            "Send a reactivation email to customers who haven't visited in 30+ "
            "days. This contacts customers, so it requires the owner to confirm "
            "before sending."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_double_stamp",
        "description": (
            "Create and activate a double-stamp campaign for a date window. "
            "Infer the dates from the request using today's date (in the system "
            "prompt) — e.g. 'this weekend' is the coming Saturday and Sunday. "
            "Provide starts_at and ends_at as ISO datetimes. Requires the owner "
            "to confirm before creating."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "starts_at": {"type": "string", "description": "ISO 8601 datetime"},
                "ends_at": {"type": "string", "description": "ISO 8601 datetime"},
                "multiplier": {"type": "integer", "minimum": 2, "maximum": 10},
            },
            "required": ["starts_at", "ends_at"],
        },
    },
    {
        "name": "send_monthly_report",
        "description": (
            "Send the owner their monthly report PDF on WhatsApp. Defaults to "
            "the previous complete month if no month/year is given. This goes to "
            "the owner only — no confirmation needed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "integer", "minimum": 1, "maximum": 12},
                "year": {"type": "integer"},
            },
        },
    },
]


def _can_mutate(tenant: dict[str, Any]) -> bool:
    return trial_service.compute_trial_status(tenant) not in {"expired", "inactive"}


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


# ---------------------------------------------------------------------------
# Dispatch from the tool-use loop
# ---------------------------------------------------------------------------


def handle_write_tool(
    *,
    name: str,
    tenant_id: str,
    phone: str,
    tenant: dict[str, Any],
    tool_input: dict[str, Any],
    now: datetime,
) -> str:
    """Called by the bot dispatch for a write tool. Direct actions run now;
    confirmable actions register a pending action and return a confirmation
    prompt for Claude to relay."""
    if name == "send_monthly_report":
        return _send_monthly_report(tenant_id, phone, tool_input, now)

    if not _can_mutate(tenant):
        return (
            "This action needs an active subscription. Tell the user their trial "
            "or subscription is inactive, so you can't send messages or create "
            "campaigns until they reactivate billing."
        )

    if name == "send_reactivation":
        return _prepare_reactivation(tenant_id, phone, now)
    if name == "create_double_stamp":
        return _prepare_double_stamp(phone, tool_input, now)
    return "Unknown action."


def _store_pending(phone: str, action: dict[str, Any], now: datetime) -> None:
    whatsapp.set_pending_action(phone, action, now + timedelta(minutes=PENDING_TTL_MINUTES))


def _prepare_reactivation(tenant_id: str, phone: str, now: datetime) -> str:
    eligible = customers.find_inactive_for_reactivation(
        tenant_id=tenant_id,
        inactive_cutoff=now - timedelta(days=reactivation_service.INACTIVE_AFTER_DAYS),
        cooldown_cutoff=now - timedelta(days=reactivation_service.COOLDOWN_DAYS),
        limit=reactivation_service.PER_TENANT_LIMIT,
    )
    count = len(eligible)
    summary = (
        f"send a reactivation email to {count} customer(s) who haven't visited "
        "in 30+ days"
    )
    _store_pending(phone, {"tool": "send_reactivation"}, now)
    return (
        f"CONFIRMATION NEEDED. Tell the user this will {summary}, and ask them to "
        "reply SIM to confirm or NÃO to cancel."
    )


def _prepare_double_stamp(phone: str, tool_input: dict[str, Any], now: datetime) -> str:
    starts = _parse_iso(tool_input.get("starts_at"))
    ends = _parse_iso(tool_input.get("ends_at"))
    if starts is None or ends is None:
        return "Tell the user you couldn't understand the campaign dates; ask them to restate."
    try:
        multiplier = int(tool_input.get("multiplier") or DEFAULT_MULTIPLIER)
    except (TypeError, ValueError):
        multiplier = DEFAULT_MULTIPLIER
    name = (tool_input.get("name") or "Double Stamp").strip()[:80] or "Double Stamp"

    action = {
        "tool": "create_double_stamp",
        "name": name,
        "starts_at": starts.isoformat(),
        "ends_at": ends.isoformat(),
        "multiplier": multiplier,
    }
    _store_pending(phone, action, now)
    summary = (
        f"create a {multiplier}x stamp campaign '{name}' from "
        f"{starts.date().isoformat()} to {ends.date().isoformat()}"
    )
    return (
        f"CONFIRMATION NEEDED. Tell the user this will {summary}, and ask them to "
        "reply SIM to confirm or NÃO to cancel."
    )


def _send_monthly_report(
    tenant_id: str, phone: str, tool_input: dict[str, Any], now: datetime
) -> str:
    month = tool_input.get("month")
    year = tool_input.get("year")
    if not (isinstance(month, int) and isinstance(year, int)):
        year, month = monthly_report_service.resolve_previous_complete_month(now)
    try:
        report = monthly_report_service.compute(tenant_id=tenant_id, year=year, month=month)
        pdf_bytes = pdf_renderer.render_monthly_report(report)
        filename = pdf_renderer.report_filename(report)
        sent = whatsapp_client.send_document(to=phone, content=pdf_bytes, filename=filename)
    except Exception as exc:
        log.exception("bot_monthly_report_failed", tenant_id=tenant_id, error=str(exc))
        return "Tell the user the report couldn't be generated right now."
    if sent is None:
        return (
            "The report was generated but WhatsApp document sending isn't "
            "available right now — tell the user to check the dashboard instead."
        )
    return "Tell the user their monthly report PDF has been sent to this chat."


# ---------------------------------------------------------------------------
# Execution after confirmation
# ---------------------------------------------------------------------------


def execute_action(tenant_id: str, action: dict[str, Any], *, now: datetime) -> str:
    """Run a previously-confirmed pending action. Returns a user-facing result
    string (already phrased — the confirmation path doesn't go back through
    Claude)."""
    tool = action.get("tool")
    if tool == "send_reactivation":
        result = reactivation_service.run_for_tenant(tenant_id, now=now)
        return f"Done — sent reactivation emails to {result.sent} customer(s)."
    if tool == "create_double_stamp":
        starts = _parse_iso(action.get("starts_at"))
        ends = _parse_iso(action.get("ends_at"))
        if starts is None or ends is None:
            return "Sorry, the campaign dates were invalid. Please try again."
        try:
            campaign_service.create_double_stamp(
                tenant_id=tenant_id,
                name=str(action.get("name") or "Double Stamp"),
                multiplier=int(action.get("multiplier") or DEFAULT_MULTIPLIER),
                starts_at=starts,
                ends_at=ends,
                status="active",
            )
        except campaign_service.ConflictingCampaignError:
            return (
                "You already have an active double-stamp campaign. "
                "Pause it first, then try again."
            )
        except campaign_service.InvalidCampaignError as exc:
            return f"Couldn't create the campaign: {exc!s}"
        return "Done — your double-stamp campaign is now active."
    return "That action is no longer available."
