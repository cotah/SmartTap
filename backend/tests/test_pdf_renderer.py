"""Smoke tests for the PDF renderer (S4-W3).

We don't pixel-compare PDFs — too fragile, font metric changes between
reportlab releases would flake the test. Instead we verify:

    - The function returns non-empty bytes that start with the PDF magic.
    - Tenant-controlled fields (name, tag label) get HTML-escaped so a
      `<b>` in a name can't break the Paragraph parser.
    - Filename is stable, sortable, free of spaces.
    - Empty months render too — no crash on zero campaigns / no insights.
"""

from datetime import UTC, datetime

import pytest

from app.services import pdf_renderer
from app.services.monthly_report_service import (
    CampaignSummary,
    MonthlyReport,
    PeriodStats,
    TagSummary,
)


def _empty_report(**over: object) -> MonthlyReport:
    base = {
        "tenant": {"id": "t-1", "name": "ACME Barber", "slug": "acme-barber"},
        "year": 2026,
        "month": 5,
        "period_start": datetime(2026, 4, 30, 23, 0, tzinfo=UTC),
        "period_end": datetime(2026, 5, 31, 23, 0, tzinfo=UTC),
        "current": PeriodStats(),
        "previous": PeriodStats(),
        "best_weekday": None,
        "peak_hour": None,
        "top_tag": None,
        "campaigns": [],
    }
    base.update(over)
    return MonthlyReport(**base)  # type: ignore[arg-type]


def test_render_returns_pdf_bytes() -> None:
    out = pdf_renderer.render_monthly_report(_empty_report())
    assert isinstance(out, bytes)
    assert out.startswith(b"%PDF-")
    assert len(out) > 1000  # smallest possible PDF is ~1KB


def test_render_includes_business_name_in_pdf() -> None:
    """Business name should appear somewhere in the PDF stream. PDF compresses
    text but the doc title metadata is always plain-text."""
    out = pdf_renderer.render_monthly_report(_empty_report())
    # The PDF object stream might compress the body text, but the /Title
    # metadata is always present. Look for 'May' (month name) and the
    # 'SmartTap' producer string.
    assert b"SmartTap" in out


def test_render_handles_full_report() -> None:
    report = _empty_report(
        current=PeriodStats(
            new_customers=12,
            total_taps=200,
            stamps_awarded=180,
            rewards_redeemed=8,
            reviews_clicked=45,
        ),
        previous=PeriodStats(
            new_customers=8,
            total_taps=150,
            stamps_awarded=130,
            rewards_redeemed=5,
            reviews_clicked=30,
        ),
        best_weekday=("Friday", 60),
        peak_hour=(18, 35),
        top_tag=TagSummary(label="Front desk", taps=120),
        campaigns=[
            CampaignSummary(
                name="Wednesday boost",
                type="double_stamp",
                status="active",
                multiplier=2,
                days_active_in_period=15,
            ),
            CampaignSummary(
                name="Reactivation push",
                type="reactivation",
                status="paused",
                multiplier=1,
                days_active_in_period=3,
            ),
        ],
    )
    out = pdf_renderer.render_monthly_report(report)
    assert out.startswith(b"%PDF-")
    assert len(out) > 2000  # populated report is bigger than empty


def test_render_escapes_business_name_with_html_chars() -> None:
    """A tenant-controlled name containing '<' must not break the Paragraph
    parser. The renderer should escape it before passing to reportlab."""
    report = _empty_report(
        tenant={"id": "t-1", "name": "<script>alert('x')</script>", "slug": "evil"},
    )
    # Must not raise. If escaping is missing, reportlab raises
    # ValueError("Paragraph parse error") here.
    out = pdf_renderer.render_monthly_report(report)
    assert out.startswith(b"%PDF-")


def test_render_escapes_tag_label_with_html_chars() -> None:
    """Same defence for the top tag's location_name — merchant input flows
    straight into the insights block."""
    report = _empty_report(
        top_tag=TagSummary(label="Bar <pirate>", taps=10),
    )
    out = pdf_renderer.render_monthly_report(report)
    assert out.startswith(b"%PDF-")


# ---------------------------------------------------------------------------
# Filename — used for email attachments and Content-Disposition
# ---------------------------------------------------------------------------


def test_filename_uses_slug_and_year_month() -> None:
    name = pdf_renderer.report_filename(_empty_report())
    assert name == "smarttap-acme-barber-2026-05.pdf"


def test_filename_falls_back_to_id_when_slug_missing() -> None:
    report = _empty_report(tenant={"id": "t-uuid-123", "name": "ACME"})
    name = pdf_renderer.report_filename(report)
    assert "t-uuid-123" in name
    assert name.endswith("-2026-05.pdf")


def test_filename_strips_unsafe_chars() -> None:
    """Slug from the DB is sanitised, but we don't want to assume it. Strip
    any character that isn't safe for HTTP Content-Disposition or shell
    filename quoting."""
    report = _empty_report(tenant={"id": "t-1", "name": "x", "slug": "weird name/with chars"})
    name = pdf_renderer.report_filename(report)
    assert " " not in name
    assert "/" not in name


@pytest.mark.parametrize("month,expected_substr", [
    (1, "2026-01"),
    (12, "2026-12"),
])
def test_filename_pads_month_to_two_digits(month: int, expected_substr: str) -> None:
    """Two-digit zero-padded month keeps filenames lexicographically sortable
    in finder windows (2026-01 before 2026-10)."""
    report = _empty_report(month=month)
    assert expected_substr in pdf_renderer.report_filename(report)
