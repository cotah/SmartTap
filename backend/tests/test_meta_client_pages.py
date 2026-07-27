"""Tests for meta_client.list_page_connections (the Page Picker resolver).

Replaces the old resolve_page_connection "first qualifying page" behaviour:
the callback needs ALL qualifying pages so the owner can pick one when their
Facebook user manages more than one. Also pins down log hygiene — the
multiple-pages log must list page metadata but never access tokens.
"""

from typing import Any

import pytest

from app.services import meta_client


def _graph_page(
    page_id: str,
    name: str = "Page",
    token: str | None = "PAT",
    ig_id: str | None = "ig-1",
    ig_username: str | None = "shop.ig",
) -> dict[str, Any]:
    page: dict[str, Any] = {"id": page_id, "name": name}
    if token is not None:
        page["access_token"] = token
    if ig_id is not None:
        page["instagram_business_account"] = {"id": ig_id}
        if ig_username is not None:
            page["instagram_business_account"]["username"] = ig_username
    return page


def _mock_accounts(
    monkeypatch: pytest.MonkeyPatch, pages: list[dict[str, Any]], calls: dict[str, Any]
) -> None:
    class Resp:
        def raise_for_status(self) -> None: ...
        def json(self) -> dict[str, Any]:
            return {"data": pages}

    def fake_get(url: str, **kw: Any) -> Resp:
        calls["url"] = url
        calls["params"] = kw.get("params", {})
        return Resp()

    monkeypatch.setattr(meta_client.httpx, "get", fake_get)


def test_list_returns_all_qualifying_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    _mock_accounts(
        monkeypatch,
        [
            _graph_page("p1", "Barber One", "PAT-1", "ig-1", "barber.one"),
            _graph_page("p2", "Barber Two", "PAT-2", "ig-2", "barber.two"),
        ],
        calls,
    )

    pages = meta_client.list_page_connections("UT-1")

    assert pages == [
        {
            "facebook_page_id": "p1",
            "page_name": "Barber One",
            "instagram_business_account_id": "ig-1",
            "ig_username": "barber.one",
            "page_access_token": "PAT-1",
        },
        {
            "facebook_page_id": "p2",
            "page_name": "Barber Two",
            "instagram_business_account_id": "ig-2",
            "ig_username": "barber.two",
            "page_access_token": "PAT-2",
        },
    ]


def test_list_requests_ig_username_field(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    _mock_accounts(monkeypatch, [], calls)

    meta_client.list_page_connections("UT-1")

    assert calls["params"]["fields"] == (
        "id,name,access_token,instagram_business_account{id,username}"
    )


def test_list_filters_pages_without_ig_or_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    _mock_accounts(
        monkeypatch,
        [
            _graph_page("p1", ig_id=None),  # no IG account linked
            _graph_page("p2", token=None),  # no access token
            _graph_page("p3", "Keeper", "PAT-3", "ig-3", None),  # no username: still ok
        ],
        calls,
    )

    pages = meta_client.list_page_connections("UT-1")

    assert pages is not None
    assert [p["facebook_page_id"] for p in pages] == ["p3"]
    assert pages[0]["ig_username"] is None


def test_list_returns_none_on_request_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(url: str, **kw: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(meta_client.httpx, "get", fake_get)

    assert meta_client.list_page_connections("UT-1") is None


def test_multiple_pages_log_lists_pages_without_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    _mock_accounts(
        monkeypatch,
        [
            _graph_page("p1", "One", "SECRET-1", "ig-1", "one"),
            _graph_page("p2", "Two", "SECRET-2", "ig-2", "two"),
        ],
        calls,
    )
    logged: dict[str, Any] = {}

    class FakeLog:
        def info(self, event: str, **kw: Any) -> None:
            logged[event] = kw

        def warning(self, event: str, **kw: Any) -> None:
            logged[event] = kw

    monkeypatch.setattr(meta_client, "log", FakeLog())

    meta_client.list_page_connections("UT-1")

    entry = logged["meta_multiple_instagram_pages"]
    assert entry["pages"] == [
        {"page_id": "p1", "name": "One", "ig_id": "ig-1", "ig_username": "one"},
        {"page_id": "p2", "name": "Two", "ig_id": "ig-2", "ig_username": "two"},
    ]
    assert "SECRET-1" not in str(entry) and "SECRET-2" not in str(entry)
