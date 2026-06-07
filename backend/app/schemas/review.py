"""Pydantic models for the review-responses dashboard API (S5 Feature 3)."""

from pydantic import BaseModel, Field


class ReviewOut(BaseModel):
    id: str
    google_review_id: str
    author: str | None
    rating: int | None
    comment: str | None
    created_at_google: str | None
    ai_draft: str | None
    reply_text: str | None
    status: str
    published_at: str | None
    created_at: str


class ReviewListResponse(BaseModel):
    items: list[ReviewOut]


class RatingBucket(BaseModel):
    rating: int = Field(ge=1, le=5)
    count: int = Field(ge=0)


class ReviewStats(BaseModel):
    total: int = Field(ge=0)
    rated_count: int = Field(ge=0)
    average: float | None
    distribution: list[RatingBucket]  # ordered 5★ → 1★


class ReplyUpdateIn(BaseModel):
    """Owner-edited reply text before publishing."""

    reply_text: str = Field(min_length=1, max_length=4000)
