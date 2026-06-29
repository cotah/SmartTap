# ruff: noqa: E501
# Email HTML is intentionally long inline — breaking it across short lines
# introduces whitespace differences that some email clients render visibly.
"""Transactional email templates.

Each function returns a `RenderedEmail` with subject, HTML, and a plain-text
fallback. Templates are deliberately inline-styled because email clients
strip <style> tags and ignore external CSS.

Design rules (don't change without alignment):
    - Container 600px, single column, centered
    - Dark Electric hybrid: dark header (#0A0A0F) + cyan CTA (#00D4FF), light body
      (full-dark bodies render inconsistently — Outlook ignores bg-color, Gmail/
      Apple auto-invert — so the card stays light; only the header strip and the
      OTP chip are dark, with bgcolor attrs)
    - One primary CTA per email, rendered bulletproof (VML roundrect for Outlook)
    - Cyan never carries small text on the light body (fails contrast) — it's used
      for fills (CTA, monogram, step badges) only; the eyebrow uses a dark teal
    - System sans-serif stack (no @font-face in email)
    - No emojis, no exclamation marks in subjects
"""

from dataclasses import dataclass
from typing import Any

# Public site URL used in email CTAs. Hard-coded rather than read from env so
# that the same template renders the same string in prod, in tests, and in
# CI — the linking target IS the prod URL because emails always reach a real
# inbox eventually. Local dev with Resend "delivered" sandbox stays consistent.
SITE_URL = "https://smarttap.ie"
SUPPORT_EMAIL = "support@smarttap.ie"

# Dark Electric (hybrid email) palette.
DARK = "#0A0A0F"  # header strip + CTA text + OTP chip bg
CYAN = "#00D4FF"  # fills only — CTA, monogram, step badges
PAGE_BG = "#EEF1F4"  # cool light grey canvas behind the card
CARD = "#FFFFFF"
INK = "#1A1A1A"  # body text
MUTED = "#6B7280"  # secondary text / footer
BORDER = "#E6E8EB"  # hairlines
EYEBROW = "#0E7490"  # dark teal — cyan family, but passes contrast for small text
WARN_BG = "#FFF7ED"
WARN_BAR = "#F59E0B"
INFO_BG = "#ECFBFF"

# Modern system stack — degrades gracefully everywhere; Inter only if installed.
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,Helvetica,Arial,sans-serif"

# Kept for back-compat with anything importing the old names.
OFF_WHITE = PAGE_BG
BLACK = INK
GREY = MUTED


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def _escape(value: str) -> str:
    """Minimal HTML escape for values we interpolate. Email clients are
    aggressive about sanitisation — being explicit here means we don't rely
    on their best-effort behaviour."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _format_cents(amount_cents: Any, currency: str = "eur") -> str:
    """Stripe sends amounts as integer minor units. We accept None and odd
    types defensively — Stripe occasionally returns 0 vs None and webhook
    payloads can be re-shaped between API versions."""
    try:
        cents = int(amount_cents)
    except (TypeError, ValueError):
        return "—"
    symbol = "€" if currency.lower() == "eur" else currency.upper() + " "
    return f"{symbol}{cents / 100:,.2f}"


def _greeting(tenant: dict[str, Any]) -> str:
    """Use the business name if it looks customised, otherwise generic.
    "My business" is the default we set at bootstrap before onboarding."""
    name = (tenant.get("name") or "").strip()
    if not name or name.lower() == "my business":
        return "Hi there,"
    return f"Hi {_escape(name)} team,"


# ---------------------------------------------------------------------------
# Reusable content blocks
# ---------------------------------------------------------------------------


def _eyebrow(label: str) -> str:
    return f'<p style="margin:0 0 10px 0;font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:700;color:{EYEBROW};">{_escape(label)}</p>'


def _h1(text: str) -> str:
    return f'<h1 style="margin:0 0 16px 0;font-size:24px;line-height:1.25;font-weight:700;color:{INK};">{text}</h1>'


def _button(label: str, url: str) -> str:
    """Bulletproof CTA — a VML roundrect so Outlook renders a real pill button,
    with a styled anchor for every other client."""
    safe_label = _escape(label)
    safe_url = _escape(url)
    width = 56 + len(label) * 9  # rough px width for the Outlook VML box
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:28px 0 4px 0;"><tr><td>
      <!--[if mso]>
      <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{safe_url}" style="height:46px;v-text-anchor:middle;width:{width}px;" arcsize="50%" stroke="f" fillcolor="{CYAN}">
        <w:anchorlock/>
        <center style="color:{DARK};font-family:Helvetica,Arial,sans-serif;font-size:14px;font-weight:bold;">{safe_label}</center>
      </v:roundrect>
      <![endif]-->
      <!--[if !mso]><!-->
      <a href="{safe_url}" style="display:inline-block;background-color:{CYAN};color:{DARK};text-decoration:none;padding:13px 30px;border-radius:999px;font-weight:700;font-size:14px;">{safe_label}</a>
      <!--<![endif]-->
    </td></tr></table>"""


def _detail_table(rows: list[tuple[str, str]]) -> str:
    """A bordered key/value box — reads like a real receipt."""
    cells = ""
    for i, (key, value) in enumerate(rows):
        top = "" if i == 0 else f"border-top:1px solid {BORDER};"
        cells += (
            f'<tr>'
            f'<td style="padding:11px 16px;{top}font-size:14px;color:{MUTED};">{_escape(key)}</td>'
            f'<td align="right" style="padding:11px 16px;{top}font-size:14px;font-weight:600;color:{INK};">{_escape(value)}</td>'
            f'</tr>'
        )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 4px 0;border:1px solid {BORDER};border-radius:10px;">{cells}</table>'


def _steps(items: list[str]) -> str:
    """Numbered next-steps list with cyan number badges."""
    rows = ""
    for i, item in enumerate(items, start=1):
        rows += f"""<tr>
          <td valign="top" width="36" style="padding:7px 12px 7px 0;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
              <td bgcolor="{CYAN}" width="24" height="24" align="center" valign="middle" style="background-color:{CYAN};border-radius:12px;width:24px;height:24px;color:{DARK};font-size:12px;font-weight:700;font-family:{FONT};">{i}</td>
            </tr></table>
          </td>
          <td valign="middle" style="padding:7px 0;font-size:14px;color:{INK};">{_escape(item)}</td>
        </tr>"""
    return f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:6px 0 8px 0;">{rows}</table>'


def _callout(text_html: str, *, tone: str = "info") -> str:
    bg = WARN_BG if tone == "warning" else INFO_BG
    bar = WARN_BAR if tone == "warning" else CYAN
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0;"><tr><td style="background-color:{bg};border-left:3px solid {bar};border-radius:8px;padding:12px 16px;font-size:14px;line-height:1.5;color:{INK};">{text_html}</td></tr></table>'


# ---------------------------------------------------------------------------
# Headers & footers
# ---------------------------------------------------------------------------


def _smarttap_header() -> str:
    """ST monogram (cyan rounded square) + wordmark, drawn in pure HTML so it
    renders identically everywhere with no hosted image dependency."""
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
      <td valign="middle" style="padding-right:10px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
          <td bgcolor="{CYAN}" width="36" height="36" align="center" valign="middle" style="background-color:{CYAN};border-radius:9px;width:36px;height:36px;color:{DARK};font-size:15px;font-weight:800;font-family:{FONT};letter-spacing:0.5px;">ST</td>
        </tr></table>
      </td>
      <td valign="middle" style="color:#FFFFFF;font-size:18px;font-weight:700;letter-spacing:0.3px;font-family:{FONT};">SmartTap</td>
    </tr></table>"""


def _merchant_header(business: str) -> str:
    """White-label header — the merchant's name, no SmartTap cyan."""
    return f'<p style="margin:0;color:#FFFFFF;font-size:13px;letter-spacing:3px;text-transform:uppercase;font-weight:700;font-family:{FONT};">{_escape(business)}</p>'


def _smarttap_footer() -> str:
    return f"""<p style="margin:0;font-weight:600;color:{INK};">SmartTap</p>
      <p style="margin:4px 0 0 0;">Tap. Connect. Grow. · Dublin, Ireland</p>
      <p style="margin:12px 0 0 0;">Need a hand? <a href="mailto:{SUPPORT_EMAIL}" style="color:{MUTED};text-decoration:underline;">{SUPPORT_EMAIL}</a></p>
      <p style="margin:6px 0 0 0;">You're receiving this because you signed up as the owner of a SmartTap account.</p>"""


def _merchant_footer(business: str, opt_out_url: str) -> str:
    return f"""<p style="margin:0;">You're getting this because you opted in at {_escape(business)}.</p>
      <p style="margin:6px 0 0 0;">Sent via SmartTap · <a href="{_escape(opt_out_url)}" style="color:{MUTED};text-decoration:underline;">Don't email me again</a></p>"""


# ---------------------------------------------------------------------------
# Shell — single document used by every template
# ---------------------------------------------------------------------------


def _shell(*, preheader: str, header_html: str, body_html: str, footer_html: str) -> str:
    return f"""<!doctype html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<!--[if mso]><style>* {{font-family:Helvetica,Arial,sans-serif !important;}}</style><![endif]-->
<title>SmartTap</title>
</head>
<body style="margin:0;padding:0;background-color:{PAGE_BG};font-family:{FONT};color:{INK};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{_escape(preheader)}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{PAGE_BG};">
    <tr><td align="center" style="padding:32px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:{CARD};border-radius:14px;overflow:hidden;border:1px solid {BORDER};">
        <tr><td bgcolor="{DARK}" style="background-color:{DARK};padding:22px 28px;">
          {header_html}
        </td></tr>
        <tr><td style="padding:36px 28px 32px 28px;font-size:15px;line-height:1.6;color:{INK};">
          {body_html}
        </td></tr>
        <tr><td style="padding:22px 28px;border-top:1px solid {BORDER};font-size:12px;line-height:1.6;color:{MUTED};">
          {footer_html}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _smarttap_doc(
    *,
    preheader: str,
    eyebrow: str,
    body_html: str,
    cta: tuple[str, str] | None = None,
) -> str:
    cta_html = _button(*cta) if cta else ""
    return _shell(
        preheader=preheader,
        header_html=_smarttap_header(),
        body_html=_eyebrow(eyebrow) + body_html + cta_html,
        footer_html=_smarttap_footer(),
    )


def _merchant_doc(
    *,
    preheader: str,
    business: str,
    body_html: str,
    cta: tuple[str, str],
    opt_out_url: str,
) -> str:
    return _shell(
        preheader=preheader,
        header_html=_merchant_header(business),
        body_html=body_html + _button(*cta),
        footer_html=_merchant_footer(business, opt_out_url),
    )


# ---------------------------------------------------------------------------
# Plan labels
# ---------------------------------------------------------------------------


_PLAN_LABELS = {
    "trial": "Trial",
    "review": "SmartReview",
    "loyalty": "SmartLoyalty",
    "pro": "SmartPro",
    "network": "SmartNetwork",
}


def _plan_display_name(plan: Any) -> str:
    if not isinstance(plan, str):
        return "SmartTap"
    return _PLAN_LABELS.get(plan, plan.title())


# ---------------------------------------------------------------------------
# SmartTap → owner templates
# ---------------------------------------------------------------------------


def welcome_email(*, tenant: dict[str, Any]) -> RenderedEmail:
    name = tenant.get("name") or "your business"
    body_html = (
        _h1("Welcome to SmartTap")
        + f'<p style="margin:0 0 14px 0;">{_greeting(tenant)}</p>'
        + f'<p style="margin:0 0 14px 0;">Your account for <strong>{_escape(name)}</strong> is ready. You have <strong>30 days</strong> to set up your loyalty programme, place your stand on the counter and watch returning customers grow.</p>'
        + '<p style="margin:0 0 8px 0;">Three quick steps to go live:</p>'
        + _steps(
            [
                "Connect your Google Business profile",
                "Choose the reward you want to offer",
                "Place your SmartTap stand on the counter",
            ]
        )
    )
    text = (
        "Welcome to SmartTap\n\n"
        "Hi there,\n\n"
        f"Your account for {name} is ready. You have 30 days to set up your loyalty programme and watch returning customers grow.\n\n"
        "Three quick steps to go live:\n"
        "1. Connect your Google Business profile\n"
        "2. Choose the reward you want to offer\n"
        "3. Place your SmartTap stand on the counter\n\n"
        f"Open the dashboard: {SITE_URL}/dashboard\n\n"
        "— SmartTap, Dublin"
    )
    return RenderedEmail(
        subject=f"Welcome to SmartTap, {name}",
        html=_smarttap_doc(
            preheader=f"Your SmartTap account for {name} is ready. 30-day trial started.",
            eyebrow="Welcome",
            body_html=body_html,
            cta=("Open dashboard", f"{SITE_URL}/dashboard"),
        ),
        text=text,
    )


def payment_succeeded_email(
    *,
    tenant: dict[str, Any],
    plan: str | None,
    amount_total: Any,
    currency: str,
) -> RenderedEmail:
    plan_label = _plan_display_name(plan or tenant.get("plan"))
    amount_str = _format_cents(amount_total, currency)
    body_html = (
        _h1("Your subscription is active")
        + f'<p style="margin:0 0 14px 0;">{_greeting(tenant)}</p>'
        + f'<p style="margin:0 0 14px 0;">Thanks for upgrading to <strong>{_escape(plan_label)}</strong>. Here is your receipt:</p>'
        + _detail_table(
            [
                ("Plan", plan_label),
                ("Amount charged", amount_str),
                ("Status", "Active"),
            ]
        )
        + '<p style="margin:16px 0 0 0;">You can change plan, download invoices or update your card any time from the billing portal.</p>'
    )
    text = (
        "Your SmartTap subscription is active\n\n"
        f"Thanks for upgrading to {plan_label}. We charged {amount_str} and your subscription is now active.\n\n"
        f"Manage billing: {SITE_URL}/dashboard/billing"
    )
    return RenderedEmail(
        subject="Your SmartTap subscription is active",
        html=_smarttap_doc(
            preheader=f"Upgrade to {plan_label} confirmed — {amount_str} charged.",
            eyebrow="Receipt",
            body_html=body_html,
            cta=("View billing", f"{SITE_URL}/dashboard/billing"),
        ),
        text=text,
    )


def payment_failed_email(
    *,
    tenant: dict[str, Any],
    amount_due: Any,
    currency: str,
) -> RenderedEmail:
    amount_str = _format_cents(amount_due, currency)
    body_html = (
        _h1("We couldn't charge your card")
        + f'<p style="margin:0 0 14px 0;">{_greeting(tenant)}</p>'
        + f'<p style="margin:0 0 4px 0;">A payment of <strong>{_escape(amount_str)}</strong> for your SmartTap subscription was declined.</p>'
        + _callout(
            "Stripe will retry automatically over the next few days. To avoid any interruption, update your payment method now.",
            tone="warning",
        )
    )
    text = (
        "We couldn't charge your card for SmartTap\n\n"
        f"A payment of {amount_str} was declined. Stripe will retry automatically.\n\n"
        f"Update your payment method: {SITE_URL}/dashboard/billing"
    )
    return RenderedEmail(
        subject="We couldn't charge your card for SmartTap",
        html=_smarttap_doc(
            preheader=f"Payment of {amount_str} was declined. Update your card to keep things running.",
            eyebrow="Action needed",
            body_html=body_html,
            cta=("Update payment method", f"{SITE_URL}/dashboard/billing"),
        ),
        text=text,
    )


def subscription_canceled_email(*, tenant: dict[str, Any]) -> RenderedEmail:
    body_html = (
        _h1("Your subscription was canceled")
        + f'<p style="margin:0 0 14px 0;">{_greeting(tenant)}</p>'
        + '<p style="margin:0 0 14px 0;">We\'ve confirmed the cancellation of your SmartTap subscription. Your data stays safe — nothing is deleted — and your NFC tags will keep working for your customers.</p>'
        + '<p style="margin:0 0 14px 0;">If you change your mind, you can resubscribe in one click any time.</p>'
    )
    text = (
        "Your SmartTap subscription was canceled\n\n"
        "We've confirmed the cancellation. Your data stays safe and your NFC tags keep working for your customers.\n\n"
        f"Resubscribe any time: {SITE_URL}/dashboard/billing"
    )
    return RenderedEmail(
        subject="Your SmartTap subscription was canceled",
        html=_smarttap_doc(
            preheader="Cancellation confirmed. Your data and NFC tags stay live.",
            eyebrow="Subscription",
            body_html=body_html,
            cta=("Resubscribe", f"{SITE_URL}/dashboard/billing"),
        ),
        text=text,
    )


def monthly_report_email(
    *, tenant: dict[str, Any], year: int, month: int
) -> RenderedEmail:
    """Sent on the 1st of each Dublin month with the previous month's PDF."""
    import calendar

    business = (tenant.get("name") or "your business").strip()
    month_name = calendar.month_name[month] if 1 <= month <= 12 else str(month)
    period_label = f"{month_name} {year}"

    body_html = (
        _h1(f"Your {_escape(period_label)} report")
        + f'<p style="margin:0 0 14px 0;">{_greeting(tenant)}</p>'
        + f'<p style="margin:0 0 14px 0;">Your monthly SmartTap report for <strong>{_escape(business)}</strong> is attached as a PDF. Inside you\'ll find new customers, taps, stamps and rewards for {_escape(period_label)}, with comparisons to the previous month.</p>'
        + '<p style="margin:0 0 14px 0;">Open the dashboard for today\'s live numbers and to schedule campaigns for the coming month.</p>'
    )
    text = (
        f"Your {period_label} SmartTap report\n\n"
        "Hi there,\n\n"
        f"Your monthly report for {business} is attached as a PDF — new customers, taps, stamps and rewards for {period_label}.\n\n"
        f"Open the dashboard: {SITE_URL}/dashboard"
    )
    return RenderedEmail(
        subject=f"Your SmartTap report — {period_label}",
        html=_smarttap_doc(
            preheader=f"PDF attached — {business} for {period_label}.",
            eyebrow="Monthly report",
            body_html=body_html,
            cta=("Open dashboard", f"{SITE_URL}/dashboard"),
        ),
        text=text,
    )


def whatsapp_otp_email(*, code: str) -> RenderedEmail:
    """One-time code emailed to an owner linking their WhatsApp number (S5
    Feature 1). No link CTA — the action is reading the code, shown in a dark
    chip. Code is digits only; safe to interpolate."""
    safe_code = _escape(str(code))
    body_html = (
        _h1("Your WhatsApp verification code")
        + '<p style="margin:0 0 16px 0;">Hi there,</p>'
        + '<p style="margin:0 0 18px 0;">Use this code in WhatsApp to link your number to your SmartTap account:</p>'
        + f'<p style="margin:0 0 18px 0;"><span bgcolor="{DARK}" style="display:inline-block;background-color:{DARK};color:{CYAN};font-size:30px;font-weight:700;letter-spacing:8px;padding:14px 22px;border-radius:10px;font-family:{FONT};">{safe_code}</span></p>'
        + f'<p style="margin:0;color:{MUTED};font-size:13px;">This code expires in 10 minutes. If you didn\'t request it, you can ignore this email.</p>'
    )
    text = (
        "Your WhatsApp verification code\n\n"
        f"Use this code in WhatsApp to link your number: {code}\n\n"
        "It expires in 10 minutes. If you didn't request it, ignore this email.\n"
    )
    return RenderedEmail(
        subject="Your SmartTap WhatsApp code",
        html=_smarttap_doc(
            preheader="Your SmartTap WhatsApp code expires in 10 minutes.",
            eyebrow="Verification",
            body_html=body_html,
            cta=None,
        ),
        text=text,
    )


# ---------------------------------------------------------------------------
# Merchant → customer templates (white-label)
# ---------------------------------------------------------------------------


def reactivation_email(
    *,
    tenant: dict[str, Any],
    customer: dict[str, Any],
    magic_link_url: str,
    opt_out_url: str,
) -> RenderedEmail:
    """Sent on behalf of the merchant to a dormant customer.

    Tone is the merchant's, not SmartTap's — the "From" is still hello@smarttap.ie
    but the subject + body speak as if from the local business. The footer
    explicitly attributes SmartTap so it's not deceptive."""
    business = (tenant.get("name") or "us").strip()
    customer_name = (customer.get("name") or "").strip()
    greeting = (
        f"Hey {_escape(customer_name.split(' ')[0])}," if customer_name else "Hey there,"
    )
    current = int(customer.get("current_stamps") or 0)
    threshold = int(tenant.get("stamps_for_reward") or 0)
    reward = (tenant.get("reward_description") or "your reward").strip()
    stamps_remaining = max(0, threshold - current)

    progress_line = (
        f"You're <strong>{stamps_remaining}</strong> stamps away from <strong>{_escape(reward)}</strong>."
        if stamps_remaining > 0 and threshold > 0
        else f"Your reward — <strong>{_escape(reward)}</strong> — is waiting."
    )
    progress_text = (
        f"You're {stamps_remaining} stamps away from {reward}."
        if stamps_remaining > 0 and threshold > 0
        else f"Your reward — {reward} — is waiting."
    )

    body_html = (
        _h1(f"We miss you at {_escape(business)}")
        + f'<p style="margin:0 0 14px 0;">{greeting}</p>'
        + f'<p style="margin:0 0 14px 0;">It\'s been a while since your last visit to <strong>{_escape(business)}</strong>. {progress_line}</p>'
        + '<p style="margin:0 0 14px 0;">Come back and we\'ll be glad to see you.</p>'
    )
    text = (
        f"We miss you at {business}\n\n"
        f"It's been a while since your last visit to {business}.\n"
        f"{progress_text}\n\n"
        f"Show your stamps: {magic_link_url}\n\n"
        f"Don't email me again: {opt_out_url}\n"
    )
    return RenderedEmail(
        subject=f"We miss you at {business}",
        html=_merchant_doc(
            preheader=progress_text,
            business=business,
            body_html=body_html,
            cta=("Show my stamps", magic_link_url),
            opt_out_url=opt_out_url,
        ),
        text=text,
    )


def review_nudge_email(
    *,
    tenant: dict[str, Any],
    customer: dict[str, Any],
    review_url: str,
    opt_out_url: str,
) -> RenderedEmail:
    """Sent on behalf of the merchant to a customer who tapped (earned a stamp)
    but didn't click the review button within the nudge window (S5 Feature 2)."""
    business = (tenant.get("name") or "us").strip()
    customer_name = (customer.get("name") or "").strip()
    greeting = (
        f"Hey {_escape(customer_name.split(' ')[0])}," if customer_name else "Hey there,"
    )

    body_html = (
        _h1(f"Thanks for visiting {_escape(business)}")
        + f'<p style="margin:0 0 14px 0;">{greeting}</p>'
        + f'<p style="margin:0 0 14px 0;">Thanks for stopping by <strong>{_escape(business)}</strong>. If you enjoyed your visit, a quick Google review means the world to a small local business — it takes under a minute.</p>'
        + '<p style="margin:0 0 14px 0;">Tap the button below to leave one.</p>'
    )
    text = (
        f"Thanks for visiting {business}\n\n"
        "If you enjoyed your visit, a quick Google review means the world to a "
        "small local business — it takes under a minute.\n\n"
        f"Leave a review: {review_url}\n\n"
        f"Don't email me again: {opt_out_url}\n"
    )
    return RenderedEmail(
        subject=f"Thanks for visiting {business}",
        html=_merchant_doc(
            preheader=f"A quick Google review for {business} takes under a minute.",
            business=business,
            body_html=body_html,
            cta=("Leave a review", review_url),
            opt_out_url=opt_out_url,
        ),
        text=text,
    )


def visit_thankyou_email(
    *,
    tenant: dict[str, Any],
    customer: dict[str, Any],
    review_url: str | None,
    magic_link_url: str,
    opt_out_url: str,
) -> RenderedEmail:
    """Sent on behalf of the merchant the moment a tap earns a stamp.

    The warm, immediate "thanks for visiting" — it shows the customer their
    stamp progress and (when the merchant has a Google review URL) nudges a
    review, gently. White-label like reactivation/review_nudge: the "From" is
    hello@smarttap.ie but the voice is the local business, and the footer
    attributes SmartTap so it's not deceptive.

    `review_url` is optional: a Loyalty-only tenant may have none. When it's
    absent the CTA falls back to the customer's stamp card (magic link) so the
    email always has a clear next step — the path decided with Henrique."""
    business = (tenant.get("name") or "us").strip()
    customer_name = (customer.get("name") or "").strip()
    greeting = (
        f"Hey {_escape(customer_name.split(' ')[0])}," if customer_name else "Hey there,"
    )

    current = int(customer.get("current_stamps") or 0)
    threshold = int(tenant.get("stamps_for_reward") or 0)
    reward = (tenant.get("reward_description") or "your reward").strip()
    remaining = max(0, threshold - current)

    # Three progress states: reward just completed, mid-card, or no loyalty
    # programme configured (Review-only tenant) — then we simply thank them.
    if threshold > 0 and remaining == 0:
        progress_html = (
            '<p style="margin:0 0 14px 0;">You\'ve completed your card — your reward '
            f'<strong>{_escape(reward)}</strong> is ready to claim on your next visit.</p>'
        )
        progress_text = (
            f"You've completed your card — your reward {reward} is ready to claim "
            "on your next visit.\n"
        )
    elif threshold > 0:
        progress_html = (
            '<p style="margin:0 0 14px 0;">You now have '
            f'<strong>{current}/{threshold}</strong> stamps — just '
            f'<strong>{remaining}</strong> more for <strong>{_escape(reward)}</strong>.</p>'
        )
        progress_text = (
            f"You now have {current}/{threshold} stamps — just {remaining} more "
            f"for {reward}.\n"
        )
    else:
        progress_html = ""
        progress_text = ""

    # The review nudge is deliberately soft and only shown when there's a URL to
    # send them to. Omitted entirely for Loyalty-only tenants.
    review_html = (
        '<p style="margin:0 0 14px 0;">Loved your visit? A quick Google review means '
        "the world to a small local business — it takes under a minute.</p>"
        if review_url
        else ""
    )

    body_html = (
        _h1(f"Thanks for visiting {_escape(business)}")
        + f'<p style="margin:0 0 14px 0;">{greeting}</p>'
        + '<p style="margin:0 0 14px 0;">Thanks for stopping by '
        f'<strong>{_escape(business)}</strong> today.</p>'
        + progress_html
        + review_html
    )

    # CTA: review when we can, otherwise the customer's own stamp card.
    cta = (
        ("Leave a review", review_url)
        if review_url
        else ("Show my stamps", magic_link_url)
    )
    cta_line = (
        f"Leave a review: {review_url}\n"
        if review_url
        else f"Show my stamps: {magic_link_url}\n"
    )

    text = (
        f"Thanks for visiting {business}\n\n"
        f"Thanks for stopping by {business} today.\n"
        + progress_text
        + (
            "Loved your visit? A quick Google review means the world to a small "
            "local business — it takes under a minute.\n\n"
            if review_url
            else "\n"
        )
        + cta_line
        + f"\nDon't email me again: {opt_out_url}\n"
    )

    return RenderedEmail(
        subject=f"Thanks for visiting {business}",
        html=_merchant_doc(
            preheader=(
                f"You now have {current}/{threshold} stamps at {business}."
                if threshold > 0
                else f"Thanks for visiting {business}."
            ),
            business=business,
            body_html=body_html,
            cta=cta,
            opt_out_url=opt_out_url,
        ),
        text=text,
    )


# Re-exported to discourage import sprawl across the email_service.
__all__ = [
    "SITE_URL",
    "RenderedEmail",
    "monthly_report_email",
    "payment_failed_email",
    "payment_succeeded_email",
    "reactivation_email",
    "review_nudge_email",
    "subscription_canceled_email",
    "visit_thankyou_email",
    "welcome_email",
    "whatsapp_otp_email",
]
