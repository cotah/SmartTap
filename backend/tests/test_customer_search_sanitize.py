"""Test the customer-search sanitizer (S5 audit S2).

The search term is interpolated into a PostgREST `or=` ilike filter, so any
character with meaning in PostgREST filter grammar must be neutralised before
it reaches the query string.
"""

from app.db.customers import _sanitize_search


def test_strips_postgrest_significant_chars() -> None:
    # Attempt to inject an extra filter term / operator.
    out = _sanitize_search("alex,phone.gt.0")
    for ch in ",().:*":
        assert ch not in out


def test_keeps_plain_text() -> None:
    assert _sanitize_search("  Maria Silva  ") == "Maria Silva"


def test_injection_payload_neutralised() -> None:
    out = _sanitize_search("*),name.ilike.*")
    assert "," not in out and "(" not in out and ")" not in out and "*" not in out
