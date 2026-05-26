"""PDF rendering for the monthly report (S4-W3).

Uses reportlab's Platypus layer (flowable-based) rather than the low-level
Canvas, because:

    - Flowables auto-paginate. If a tenant has 20 active campaigns the table
      breaks across pages without any manual cursor math.
    - Style centralisation: changing the brand colour palette is a single-
      spot edit, not a re-flow of every drawString call.

Visual rules — kept narrow on purpose for the MVP. Charts and per-customer
breakdowns are explicit future work; if you reach for them, treat them as a
new sprint, not a tweak.

Output format: bytes (PDF) so the caller can either attach to an email or
stream via FastAPI's Response. Never writes to disk; the cron and the
dashboard download endpoint both want in-memory.
"""

import calendar
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

from app.services.monthly_report_service import (
    MonthlyReport,
    delta_pct,
)

# Brand palette mirrored from emails/templates.py — keeping the duplication
# small and explicit beats coupling the email layer to a PDF library.
GREEN = colors.HexColor("#1B4D3E")
AMBER = colors.HexColor("#E8A020")
OFF_WHITE = colors.HexColor("#F7F5F0")
BLACK = colors.HexColor("#1A1A1A")
GREY = colors.HexColor("#6B6B6B")
LIGHT_GREY = colors.HexColor("#E5E5E5")


def _styles() -> dict[str, ParagraphStyle]:
    """One sample sheet per call — reportlab mutates the returned styles, so
    sharing a module-level instance leaks edits between renders."""
    sheet = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "h1", parent=sheet["Heading1"], fontName="Helvetica-Bold",
            fontSize=22, leading=26, textColor=BLACK, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=sheet["BodyText"], fontName="Helvetica",
            fontSize=11, leading=14, textColor=GREY, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2", parent=sheet["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, leading=16, textColor=GREEN, spaceBefore=12,
            spaceAfter=6, textTransform="uppercase",
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label", parent=sheet["BodyText"], fontName="Helvetica",
            fontSize=8, leading=10, textColor=GREY,
        ),
        "kpi_value": ParagraphStyle(
            "kpi_value", parent=sheet["BodyText"], fontName="Helvetica-Bold",
            fontSize=22, leading=26, textColor=BLACK,
        ),
        "kpi_delta_up": ParagraphStyle(
            "kpi_delta_up", parent=sheet["BodyText"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=GREEN,
        ),
        "kpi_delta_down": ParagraphStyle(
            "kpi_delta_down", parent=sheet["BodyText"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=colors.HexColor("#B33A3A"),
        ),
        "kpi_delta_flat": ParagraphStyle(
            "kpi_delta_flat", parent=sheet["BodyText"], fontName="Helvetica",
            fontSize=9, leading=12, textColor=GREY,
        ),
        "body": ParagraphStyle(
            "body", parent=sheet["BodyText"], fontName="Helvetica",
            fontSize=10, leading=13, textColor=BLACK,
        ),
        "footer": ParagraphStyle(
            "footer", parent=sheet["BodyText"], fontName="Helvetica",
            fontSize=8, leading=10, textColor=GREY, alignment=1,
        ),
    }


def _format_delta(curr: int, prev: int, styles: dict[str, ParagraphStyle]) -> Paragraph:
    """Render the small "vs last month" line under each KPI value.

    Three states:
        - Previous was zero → "—" in grey (can't compute a percentage)
        - Current >= previous → green up-arrow
        - Current < previous → red down-arrow
    """
    pct = delta_pct(curr, prev)
    if pct is None:
        return Paragraph("— vs last month", styles["kpi_delta_flat"])
    if pct >= 0:
        return Paragraph(f"▲ {pct:+.0f}% vs last month", styles["kpi_delta_up"])
    return Paragraph(f"▼ {pct:+.0f}% vs last month", styles["kpi_delta_down"])


def _kpi_cell(
    label: str, value: int, prev: int, styles: dict[str, ParagraphStyle]
) -> list[Paragraph]:
    """Three stacked paragraphs per KPI cell. Returned as a list so the
    parent Table can render them as a single cell with vertical stack."""
    return [
        Paragraph(label.upper(), styles["kpi_label"]),
        Paragraph(f"{value:,}", styles["kpi_value"]),
        _format_delta(value, prev, styles),
    ]


def _kpi_grid(report: MonthlyReport, styles: dict[str, ParagraphStyle]) -> Table:
    """2x2 grid of headline KPIs. Reviews-clicked lives in the insights
    section, not here, so the KPI grid stays balanced visually."""
    c, p = report.current, report.previous
    data = [
        [_kpi_cell("New customers", c.new_customers, p.new_customers, styles),
         _kpi_cell("Total taps", c.total_taps, p.total_taps, styles)],
        [_kpi_cell("Stamps awarded", c.stamps_awarded, p.stamps_awarded, styles),
         _kpi_cell("Rewards redeemed", c.rewards_redeemed, p.rewards_redeemed, styles)],
    ]
    tbl = Table(data, colWidths=[85 * mm, 85 * mm], rowHeights=[30 * mm, 30 * mm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), OFF_WHITE),
                ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_GREY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    return tbl


def _insights_block(report: MonthlyReport, styles: dict[str, ParagraphStyle]) -> Table:
    """Three rows of single-line insights. A Table (not stacked Paragraphs)
    so the label/value columns line up nicely."""
    rows: list[list[Paragraph]] = []

    if report.best_weekday:
        name, count = report.best_weekday
        rows.append([
            Paragraph("Busiest day", styles["body"]),
            Paragraph(f"<b>{name}</b> — {count} taps", styles["body"]),
        ])
    if report.peak_hour:
        hour, count = report.peak_hour
        # 14:00 reads better than just "14" on a stand-alone line.
        rows.append([
            Paragraph("Peak hour", styles["body"]),
            Paragraph(f"<b>{hour:02d}:00</b> — {count} taps", styles["body"]),
        ])
    if report.top_tag:
        rows.append([
            Paragraph("Top NFC tag", styles["body"]),
            Paragraph(
                f"<b>{report.top_tag.label}</b> — {report.top_tag.taps} taps",
                styles["body"],
            ),
        ])
    rows.append([
        Paragraph("Google reviews clicked", styles["body"]),
        Paragraph(f"<b>{report.current.reviews_clicked:,}</b>", styles["body"]),
    ])

    tbl = Table(rows, colWidths=[50 * mm, 120 * mm])
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, LIGHT_GREY),
            ]
        )
    )
    return tbl


def _campaigns_block(report: MonthlyReport, styles: dict[str, ParagraphStyle]) -> Table:
    """Table of campaigns that overlapped the period. Renders even when
    empty so the merchant gets a clear 'no campaigns this month' signal."""
    header = [
        Paragraph("<b>Name</b>", styles["body"]),
        Paragraph("<b>Type</b>", styles["body"]),
        Paragraph("<b>Status</b>", styles["body"]),
        Paragraph("<b>Multiplier</b>", styles["body"]),
        Paragraph("<b>Days active</b>", styles["body"]),
    ]
    rows: list[list[Paragraph]] = [header]
    if not report.campaigns:
        rows.append(
            [
                Paragraph("No campaigns ran this period.", styles["body"]),
                Paragraph("—", styles["body"]),
                Paragraph("—", styles["body"]),
                Paragraph("—", styles["body"]),
                Paragraph("—", styles["body"]),
            ]
        )
    else:
        for c in report.campaigns:
            rows.append(
                [
                    Paragraph(c.name, styles["body"]),
                    Paragraph(c.type.replace("_", " "), styles["body"]),
                    Paragraph(c.status, styles["body"]),
                    Paragraph(f"×{c.multiplier}", styles["body"]),  # noqa: RUF001
                    Paragraph(str(c.days_active_in_period), styles["body"]),
                ]
            )
    tbl = Table(
        rows,
        colWidths=[55 * mm, 35 * mm, 25 * mm, 25 * mm, 30 * mm],
        repeatRows=1,
    )
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, 0), OFF_WHITE),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, GREEN),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, LIGHT_GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tbl


def _format_period_label(report: MonthlyReport) -> str:
    """e.g. 'May 2026 - 1 May - 31 May'."""
    month_name = calendar.month_name[report.month]
    last_day = calendar.monthrange(report.year, report.month)[1]
    # Middle dot + en-dash are intentional typography in the rendered PDF.
    label = f"{month_name} {report.year} · 1 {month_name} – {last_day} {month_name}"  # noqa: RUF001
    return label


def _escape(value: str) -> str:
    """Paragraph() parses a tiny HTML subset; merchant-controlled fields
    (tenant name, campaign name, tag label) must be neutralised so an
    accidental `<b>` in a name doesn't corrupt the layout."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_monthly_report(report: MonthlyReport) -> bytes:
    """Render the report as PDF bytes."""
    styles = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"SmartTap Monthly Report — {calendar.month_name[report.month]} {report.year}",
        author="SmartTap",
    )

    business = _escape((report.tenant.get("name") or "your business").strip())
    period_label = _escape(_format_period_label(report))

    flow = [
        Paragraph(business, styles["h1"]),
        Paragraph(f"Monthly report · {period_label}", styles["subtitle"]),
        HRFlowable(width="100%", thickness=1.4, color=GREEN, spaceBefore=4, spaceAfter=12),
        Paragraph("Headline numbers", styles["h2"]),
        _kpi_grid(report, styles),
        Spacer(1, 8 * mm),
        Paragraph("Insights", styles["h2"]),
        _insights_block(report, styles),
        Spacer(1, 8 * mm),
        Paragraph("Campaigns this period", styles["h2"]),
        _campaigns_block(report, styles),
        Spacer(1, 10 * mm),
        HRFlowable(width="100%", thickness=0.5, color=LIGHT_GREY, spaceBefore=2, spaceAfter=6),
        Paragraph("SmartTap · Dublin, Ireland · smarttap.ie", styles["footer"]),
    ]
    doc.build(flow)
    return buf.getvalue()


def report_filename(report: MonthlyReport) -> str:
    """Stable, sortable filename used for both email attachments and the
    dashboard download Content-Disposition. Avoids spaces so old email
    clients don't quote-mangle it."""
    slug_source = (report.tenant.get("slug") or report.tenant.get("id") or "smarttap")
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in str(slug_source))
    return f"smarttap-{slug}-{report.year:04d}-{report.month:02d}.pdf"
