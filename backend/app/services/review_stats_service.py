"""Rating summary for the reviews dashboard header (Fase C).

Aggregates every review a tenant has (any status) into an average, a total,
and a 5→1 star distribution. `summarize_ratings` is pure so the rounding and
counting rules are easy to test; `compute_stats` wires it to the db.
"""

from dataclasses import dataclass

from app.db import reviews as reviews_db

STARS = (5, 4, 3, 2, 1)


@dataclass(frozen=True)
class RatingSummary:
    total: int  # all reviews, including any without a numeric rating
    rated_count: int  # reviews with a valid 1–5 star rating
    average: float | None  # mean over rated reviews, None when none are rated
    distribution: list[tuple[int, int]]  # [(5, n), (4, n), (3, n), (2, n), (1, n)]


def summarize_ratings(ratings: list[int | None]) -> RatingSummary:
    valid = [r for r in ratings if isinstance(r, int) and 1 <= r <= 5]
    rated_count = len(valid)
    average = round(sum(valid) / rated_count, 1) if rated_count else None
    distribution = [(star, sum(1 for r in valid if r == star)) for star in STARS]
    return RatingSummary(
        total=len(ratings),
        rated_count=rated_count,
        average=average,
        distribution=distribution,
    )


def compute_stats(tenant_id: str) -> RatingSummary:
    return summarize_ratings(reviews_db.list_all_ratings(tenant_id))
