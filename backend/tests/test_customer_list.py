from typing import Any

import pytest

from app.errors import NotFoundError
from app.services import customer_service
from app.services.customer_service import ListCustomersContext, list_customers


def _row(**over: Any) -> dict[str, Any]:
    base = {
        "id": "c-1",
        "name": "Alice",
        "phone": "+353871234567",
        "current_stamps": 3,
        "total_visits": 5,
        "last_visit_at": "2026-05-20T10:00:00+00:00",
        "created_at": "2026-04-01T10:00:00+00:00",
    }
    base.update(over)
    return base


def test_list_customers_marks_reward_ready_when_at_or_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        customer_service.tenants,
        "get_by_id",
        lambda _id: {"id": "t-1", "stamps_for_reward": 10},
    )
    monkeypatch.setattr(
        customer_service.customers,
        "list_for_tenant",
        lambda **_: (
            [
                _row(id="c-low", current_stamps=3),
                _row(id="c-exact", current_stamps=10),
                _row(id="c-over", current_stamps=15),
            ],
            3,
        ),
    )

    page = list_customers(
        ListCustomersContext(
            tenant_id="t-1",
            search=None,
            filter_mode="all",
            sort="recent",
            page=1,
            limit=20,
        )
    )

    by_id = {item.id: item for item in page.items}
    assert by_id["c-low"].has_reward_ready is False
    assert by_id["c-exact"].has_reward_ready is True
    assert by_id["c-over"].has_reward_ready is True
    assert page.total == 3
    assert page.page == 1
    assert page.limit == 20


def test_list_customers_never_marks_reward_when_threshold_is_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        customer_service.tenants,
        "get_by_id",
        lambda _id: {"id": "t-1", "stamps_for_reward": 0},
    )
    monkeypatch.setattr(
        customer_service.customers,
        "list_for_tenant",
        lambda **_: ([_row(current_stamps=999)], 1),
    )

    page = list_customers(
        ListCustomersContext(
            tenant_id="t-1",
            search=None,
            filter_mode="all",
            sort="recent",
            page=1,
            limit=20,
        )
    )

    assert page.items[0].has_reward_ready is False


def test_list_customers_raises_when_tenant_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(customer_service.tenants, "get_by_id", lambda _id: None)

    with pytest.raises(NotFoundError):
        list_customers(
            ListCustomersContext(
                tenant_id="missing",
                search=None,
                filter_mode="all",
                sort="recent",
                page=1,
                limit=20,
            )
        )


def test_list_customers_passes_filters_through_to_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_list(**kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(
        customer_service.tenants,
        "get_by_id",
        lambda _id: {"id": "t-1", "stamps_for_reward": 10},
    )
    monkeypatch.setattr(customer_service.customers, "list_for_tenant", fake_list)

    list_customers(
        ListCustomersContext(
            tenant_id="t-1",
            search="alice",
            filter_mode="at_risk",
            sort="visits",
            page=2,
            limit=10,
        )
    )

    assert captured["tenant_id"] == "t-1"
    assert captured["search"] == "alice"
    assert captured["filter_mode"] == "at_risk"
    assert captured["sort"] == "visits"
    assert captured["page"] == 2
    assert captured["limit"] == 10
    assert captured["stamps_for_reward"] == 10
