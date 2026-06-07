"""Tests for the review rating summary (Fase C — Reviews summary header).

`summarize_ratings` is a pure function: it owns the average rounding, the
5→1 distribution ordering, and the rules for which rows count. Those are the
risky bits, so they're tested directly without touching the db.
"""

from typing import Any

import pytest

from app.services import review_stats_service as svc


def test_empty_has_no_average_and_zero_total() -> None:
    s = svc.summarize_ratings([])
    assert s.total == 0
    assert s.rated_count == 0
    assert s.average is None
    # distribution is always 5→1, all zero
    assert s.distribution == [(5, 0), (4, 0), (3, 0), (2, 0), (1, 0)]


def test_average_is_mean_of_ratings_rounded_to_one_decimal() -> None:
    s = svc.summarize_ratings([5, 5, 4])  # 14/3 = 4.666…
    assert s.average == 4.7
    assert s.rated_count == 3
    assert s.total == 3


def test_distribution_counts_per_star_in_5_to_1_order() -> None:
    s = svc.summarize_ratings([5, 5, 4, 3, 1, 1, 1])
    assert s.distribution == [(5, 2), (4, 1), (3, 1), (2, 0), (1, 3)]


def test_null_ratings_count_toward_total_but_not_average() -> None:
    s = svc.summarize_ratings([5, None, 3, None])
    assert s.total == 4
    assert s.rated_count == 2
    assert s.average == 4.0  # (5+3)/2
    assert s.distribution == [(5, 1), (4, 0), (3, 1), (2, 0), (1, 0)]


def test_out_of_range_ratings_are_ignored_from_average_and_bars() -> None:
    s = svc.summarize_ratings([5, 0, 6, 4])  # 0 and 6 are not valid stars
    assert s.rated_count == 2
    assert s.average == 4.5
    assert s.distribution == [(5, 1), (4, 1), (3, 0), (2, 0), (1, 0)]


def test_compute_stats_reads_db_then_summarizes(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_list_all_ratings(tenant_id: str) -> list[int | None]:
        seen["tenant_id"] = tenant_id
        return [5, 4, 4, 2]

    monkeypatch.setattr(svc.reviews_db, "list_all_ratings", fake_list_all_ratings)

    s = svc.compute_stats("t-1")

    assert seen["tenant_id"] == "t-1"
    assert s.total == 4
    assert s.average == 3.8  # (5+4+4+2)/4 = 3.75 → 3.8 (round half to even → 3.8)
    assert s.distribution == [(5, 1), (4, 2), (3, 0), (2, 1), (1, 0)]
