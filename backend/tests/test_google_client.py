"""Tests for the Google Business Profile client (S5 Feature 3).

Unit-level: no-op gating, consent URL construction, review normalisation. No
network calls (the gated API can't be hit in CI).
"""

import pytest

from app.services import google_client


class _Settings:
    google_client_id = ""
    google_client_secret = ""
    google_oauth_redirect = ""


def _patch(monkeypatch: pytest.MonkeyPatch, **over: str) -> None:
    s = _Settings()
    for k, v in over.items():
        setattr(s, k, v)
    monkeypatch.setattr(google_client, "get_settings", lambda: s)


def test_not_configured_without_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    assert google_client.is_configured() is False


def test_configured_with_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, google_client_id="id", google_client_secret="sec", google_oauth_redirect="https://x/cb")
    assert google_client.is_configured() is True


def test_consent_url_has_required_params(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, google_client_id="cid", google_client_secret="sec", google_oauth_redirect="https://api.x/cb")
    url = google_client.build_consent_url("t-1.sig")
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=cid" in url
    assert "business.manage" in url
    assert "access_type=offline" in url
    assert "state=t-1.sig" in url


def test_list_new_reviews_noop_without_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)  # not configured
    conn = {"refresh_token": "x", "account_id": "a", "location_id": "l"}
    assert google_client.list_new_reviews(conn) == []


def test_publish_reply_noop_without_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    assert google_client.publish_reply({"refresh_token": "x"}, "g1", "hi") is False


def test_list_new_reviews_noop_when_connection_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, google_client_id="cid", google_client_secret="sec", google_oauth_redirect="https://x/cb")
    # configured, but no account/location -> still no-op
    assert google_client.list_new_reviews({"refresh_token": "rt"}) == []


def test_normalise_review_maps_star_enum() -> None:
    raw = {
        "reviewId": "abc",
        "reviewer": {"displayName": "Alex"},
        "starRating": "FOUR",
        "comment": "good",
        "createTime": "2026-05-01T10:00:00Z",
    }
    norm = google_client._normalise_review(raw)
    assert norm == {
        "google_review_id": "abc",
        "author": "Alex",
        "rating": 4,
        "comment": "good",
        "created_at_google": "2026-05-01T10:00:00Z",
    }


def test_normalise_review_without_id_returns_none() -> None:
    assert google_client._normalise_review({"comment": "x"}) is None


def test_normalise_review_unknown_star_is_none_rating() -> None:
    norm = google_client._normalise_review({"reviewId": "x", "starRating": "WAT"})
    assert norm is not None
    assert norm["rating"] is None
