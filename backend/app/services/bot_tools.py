"""Read-only tools the WhatsApp bot exposes to Claude (S5 Feature 1, Phase A).

Each tool maps to an existing internal service and runs with the authenticated
`tenant_id` — which is ALWAYS injected by the bot service, never chosen by the
model. Tools never write. `execute()` returns a compact JSON string that Claude
reads to compose its natural-language answer.

Phase B will add write tools (reactivation, campaigns) with confirmation.
"""

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db import customers, taps, tenants
from app.services import dashboard_service
from app.services.monthly_report_service import DUBLIN_TZ, WEEKDAY_NAMES

# Allowed lookback windows for time-based tools. Clamp anything else to 30.
_ALLOWED_DAYS = {7, 30, 90}

# Semantic customer filter -> (db FilterMode, db SortMode).
_FILTER_MAP: dict[str, tuple[str, str]] = {
    "loyal": ("all", "visits"),
    "at_risk": ("at_risk", "recent"),
    "has_reward": ("has_reward", "stamps"),
    "new": ("all", "recent"),
    "all": ("all", "recent"),
}

MAX_CUSTOMER_LIMIT = 20


# Anthropic tool schemas. `tenant_id` is deliberately NOT a parameter — the
# backend injects it; the model can't address another tenant's data.
TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_overview",
        "description": (
            "High-level metrics for the owner's business: total customers, taps "
            "in the last 7 days, reviews in the last 30 days, customers at risk "
            "(no visit in 30+ days), and total active stamps."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "query_customers",
        "description": (
            "List customers in a segment. Use 'loyal' for the most frequent "
            "visitors, 'at_risk' for those who haven't returned in 30+ days, "
            "'has_reward' for those with enough stamps to redeem, 'new' for the "
            "most recent signups, 'all' otherwise."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "enum": ["loyal", "at_risk", "has_reward", "new", "all"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CUSTOMER_LIMIT},
            },
            "required": ["filter"],
        },
    },
    {
        "name": "get_peak_times",
        "description": (
            "The busiest weekday and hour (local Dublin time) over the last N "
            "days, based on tap activity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "enum": [7, 30, 90]}},
        },
    },
    {
        "name": "get_review_performance",
        "description": (
            "Review performance over the last N days: number of taps, number of "
            "review-button clicks, and the tap-to-review conversion rate. Note: "
            "this is click-through to Google, not the Google star rating."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "enum": [7, 30, 90]}},
        },
    },
]


def _clamp_days(value: Any) -> int:
    try:
        days = int(value)
    except (TypeError, ValueError):
        return 30
    return days if days in _ALLOWED_DAYS else 30


def execute(name: str, tenant_id: str, tool_input: dict[str, Any]) -> str:
    """Run a tool by name, scoped to tenant_id. Returns a JSON string for Claude.
    Unknown tool name returns an error payload (defensive — schema constrains
    the model, but we don't trust it blindly)."""
    if name == "get_overview":
        return _get_overview(tenant_id)
    if name == "query_customers":
        return _query_customers(tenant_id, tool_input)
    if name == "get_peak_times":
        return _get_peak_times(tenant_id, _clamp_days(tool_input.get("days", 30)))
    if name == "get_review_performance":
        return _get_review_performance(tenant_id, _clamp_days(tool_input.get("days", 30)))
    return json.dumps({"error": f"unknown tool: {name}"})


def _get_overview(tenant_id: str) -> str:
    m = dashboard_service.overview(tenant_id)
    return json.dumps(
        {
            "customers_total": m.customers_total,
            "taps_last_7_days": m.taps_week,
            "reviews_last_30_days": m.reviews_month,
            "customers_at_risk_30d": m.customers_at_risk,
            "active_stamps_total": m.active_stamps_total,
        }
    )


def _query_customers(tenant_id: str, tool_input: dict[str, Any]) -> str:
    semantic = str(tool_input.get("filter") or "all")
    filter_mode, sort = _FILTER_MAP.get(semantic, _FILTER_MAP["all"])

    raw_limit = tool_input.get("limit", 10)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, MAX_CUSTOMER_LIMIT))

    tenant = tenants.get_by_id(tenant_id) or {}
    stamps_for_reward = int(tenant.get("stamps_for_reward") or 0)

    rows, total = customers.list_for_tenant(
        tenant_id=tenant_id,
        search=None,
        filter_mode=filter_mode,  # type: ignore[arg-type]
        sort=sort,  # type: ignore[arg-type]
        page=1,
        limit=limit,
        stamps_for_reward=stamps_for_reward,
    )
    items = [
        {
            "name": r.get("name") or "(no name)",
            "total_visits": r.get("total_visits") or 0,
            "current_stamps": r.get("current_stamps") or 0,
            "last_visit_at": r.get("last_visit_at"),
        }
        for r in rows
    ]
    return json.dumps({"filter": semantic, "total_matching": total, "showing": items})


def _get_peak_times(tenant_id: str, days: int) -> str:
    now = datetime.now(UTC)
    start = now - timedelta(days=days)
    rows = taps.list_in_range(tenant_id, start=start, end=now)

    weekday_counter: Counter[int] = Counter()
    hour_counter: Counter[int] = Counter()
    for row in rows:
        created = row.get("created_at")
        if not isinstance(created, str):
            continue
        try:
            ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue
        local = ts.astimezone(DUBLIN_TZ)
        weekday_counter[local.weekday()] += 1
        hour_counter[local.hour] += 1

    if not rows or not weekday_counter:
        return json.dumps(
            {"days": days, "total_taps": len(rows), "note": "no tap activity in this window"}
        )

    wd, wd_count = weekday_counter.most_common(1)[0]
    hour, hour_count = hour_counter.most_common(1)[0]
    return json.dumps(
        {
            "days": days,
            "total_taps": len(rows),
            "busiest_weekday": {"day": WEEKDAY_NAMES[wd], "taps": wd_count},
            "peak_hour_local_dublin": {"hour_24h": hour, "taps": hour_count},
        }
    )


def _get_review_performance(tenant_id: str, days: int) -> str:
    now = datetime.now(UTC)
    start = now - timedelta(days=days)
    total_taps = taps.count_in_range(tenant_id, start=start, end=now)
    review_clicks = taps.count_in_range(
        tenant_id, start=start, end=now, action_taken="review_clicked"
    )
    conversion = round(review_clicks / total_taps, 3) if total_taps else 0.0
    return json.dumps(
        {
            "days": days,
            "total_taps": total_taps,
            "review_clicks": review_clicks,
            "tap_to_review_conversion": conversion,
            "note": "conversion is click-through to Google, not the star rating",
        }
    )
