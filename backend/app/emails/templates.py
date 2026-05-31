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
    - DM Sans falls back to system sans-serif (no @font-face in email)
    - One CTA per email; secondary links inline only
    - No emojis, no exclamation marks in subjects
"""

from dataclasses import dataclass
from typing import Any

# Public site URL used in email CTAs. Hard-coded rather than read from env so
# that the same template renders the same string in prod, in tests, and in
# CI — the linking target IS the prod URL because emails always reach a real
# inbox eventually. Local dev with Resend "delivered" sandbox stays consistent.
SITE_URL = "https://smarttap.ie"

# Dark Electric (hybrid email): dark header strip + cyan accents on a LIGHT,
# reliable body. Full-dark email bodies render inconsistently across clients
# (Outlook ignores bg-color, Gmail/Apple auto-invert), so the card stays light
# for legibility; only the header strip + OTP chip are dark (with bgcolor attrs).
DARK = "#0A0A0F"
CYAN = "#00D4FF"
OFF_WHITE = "#F7F5F0"
BLACK = "#1A1A1A"
GREY = "#6B6B6B"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def _layout(*, preheader: str, body_html: str, cta_label: str, cta_url: str) -> str:
    """Wraps body content in the shared shell (header + footer + CTA).

    Preheader is the hidden text shown in the inbox preview before the user
    opens the email — important for open rates, easy to forget.
    """
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>SmartTap</title>
</head>
<body style="margin:0;padding:0;background-color:{OFF_WHITE};font-family:'DM Sans',Helvetica,Arial,sans-serif;color:{BLACK};">
  <!-- preheader (hidden inbox preview) -->
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{_escape(preheader)}</div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{OFF_WHITE};">
    <tr><td align="center" style="padding:24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;border:1px solid rgba(0,0,0,0.06);">
        <tr><td bgcolor="{DARK}" style="background-color:{DARK};padding:20px 24px;">
          <p style="margin:0;color:{CYAN};font-size:12px;letter-spacing:4px;text-transform:uppercase;font-weight:700;">SmartTap</p>
        </td></tr>
        <tr><td style="padding:32px 24px;font-size:15px;line-height:1.55;color:{BLACK};">
          {body_html}
          <p style="margin:28px 0 0 0;">
            <a href="{_escape(cta_url)}" style="display:inline-block;background-color:{CYAN};color:{DARK};text-decoration:none;padding:12px 24px;border-radius:999px;font-weight:600;font-size:14px;">{_escape(cta_label)}</a>
          </p>
        </td></tr>
        <tr><td style="padding:20px 24px;border-top:1px solid rgba(0,0,0,0.06);font-size:12px;color:{GREY};">
          <p style="margin:0;">SmartTap · Dublin, Ireland</p>
          <p style="margin:6px 0 0 0;">You're receiving this because you signed up as the owner of a SmartTap account.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


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
# Templates
# ---------------------------------------------------------------------------


def welcome_email(*, tenant: dict[str, Any]) -> RenderedEmail:
    name = tenant.get("name") or "your business"
    body_html = f"""
        <h1 style="margin:0 0 12px 0;font-size:22px;color:{BLACK};">Welcome to SmartTap</h1>
        <p style="margin:0 0 12px 0;">{_greeting(tenant)}</p>
        <p style="margin:0 0 12px 0;">Your account for <strong>{_escape(name)}</strong> is ready. You have <strong>30 days</strong> to set up your loyalty programme, place your stand on the counter and watch returning customers grow.</p>
        <p style="margin:0 0 12px 0;">Inside the dashboard you can connect your Google Business profile, choose the reward you want to offer, and see every tap and review in one place.</p>
    """
    text = (
        f"Welcome to SmartTap\n\n"
        f"Hi there,\n\n"
        f"Your account for {name} is ready. You have 30 days to set up your loyalty programme and watch returning customers grow.\n\n"
        f"Open the dashboard: {SITE_URL}/dashboard\n\n"
        f"— SmartTap, Dublin"
    )
    return RenderedEmail(
        subject=f"Welcome to SmartTap, {name}",
        html=_layout(
            preheader=f"Your SmartTap account for {name} is ready. 30-day trial started.",
            body_html=body_html,
            cta_label="Open dashboard",
            cta_url=f"{SITE_URL}/dashboard",
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
    body_html = f"""
        <h1 style="margin:0 0 12px 0;font-size:22px;color:{BLACK};">Your subscription is active</h1>
        <p style="margin:0 0 12px 0;">{_greeting(tenant)}</p>
        <p style="margin:0 0 12px 0;">Thanks for upgrading to <strong>{_escape(plan_label)}</strong>. We charged <strong>{_escape(amount_str)}</strong> and your subscription is now active.</p>
        <p style="margin:0 0 12px 0;">You can change plan, download invoices or update your card any time from the billing portal.</p>
    """
    text = (
        f"Your SmartTap subscription is active\n\n"
        f"Thanks for upgrading to {plan_label}. We charged {amount_str} and your subscription is now active.\n\n"
        f"Manage billing: {SITE_URL}/dashboard/billing"
    )
    return RenderedEmail(
        subject="Your SmartTap subscription is active",
        html=_layout(
            preheader=f"Upgrade to {plan_label} confirmed — {amount_str} charged.",
            body_html=body_html,
            cta_label="View billing",
            cta_url=f"{SITE_URL}/dashboard/billing",
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
    body_html = f"""
        <h1 style="margin:0 0 12px 0;font-size:22px;color:{BLACK};">We couldn't charge your card</h1>
        <p style="margin:0 0 12px 0;">{_greeting(tenant)}</p>
        <p style="margin:0 0 12px 0;">A payment of <strong>{_escape(amount_str)}</strong> for your SmartTap subscription was declined.</p>
        <p style="margin:0 0 12px 0;">Stripe will retry automatically over the next few days. To avoid any interruption, update your payment method now from the billing portal.</p>
    """
    text = (
        f"We couldn't charge your card for SmartTap\n\n"
        f"A payment of {amount_str} was declined. Stripe will retry automatically.\n\n"
        f"Update your payment method: {SITE_URL}/dashboard/billing"
    )
    return RenderedEmail(
        subject="We couldn't charge your card for SmartTap",
        html=_layout(
            preheader=f"Payment of {amount_str} was declined. Update your card to keep things running.",
            body_html=body_html,
            cta_label="Update payment method",
            cta_url=f"{SITE_URL}/dashboard/billing",
        ),
        text=text,
    )


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
    greeting = f"Hey {_escape(customer_name.split(' ')[0])}," if customer_name else "Hey there,"
    current = int(customer.get("current_stamps") or 0)
    threshold = int(tenant.get("stamps_for_reward") or 0)
    reward = (tenant.get("reward_description") or "your reward").strip()
    stamps_remaining = max(0, threshold - current)

    progress_line = (
        f"You're <strong>{stamps_remaining}</strong> stamps away from "
        f"<strong>{_escape(reward)}</strong>."
        if stamps_remaining > 0 and threshold > 0
        else f"Your reward — <strong>{_escape(reward)}</strong> — is waiting."
    )
    progress_text = (
        f"You're {stamps_remaining} stamps away from {reward}."
        if stamps_remaining > 0 and threshold > 0
        else f"Your reward — {reward} — is waiting."
    )

    body_html = f"""
        <h1 style="margin:0 0 12px 0;font-size:22px;color:{BLACK};">We miss you at {_escape(business)}</h1>
        <p style="margin:0 0 12px 0;">{greeting}</p>
        <p style="margin:0 0 12px 0;">It's been a while since your last visit to <strong>{_escape(business)}</strong>. {progress_line}</p>
        <p style="margin:0 0 12px 0;">Come back and we'll be glad to see you.</p>
    """

    text = (
        f"We miss you at {business}\n\n"
        f"It's been a while since your last visit to {business}.\n"
        f"{progress_text}\n\n"
        f"Show your stamps: {magic_link_url}\n\n"
        f"Don't email me again: {opt_out_url}\n"
    )

    # The custom footer below replaces the generic one in _layout — easier
    # than parameterising _layout for this one case. We hand-roll the shell.
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{_escape(business)}</title>
</head>
<body style="margin:0;padding:0;background-color:{OFF_WHITE};font-family:'DM Sans',Helvetica,Arial,sans-serif;color:{BLACK};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{progress_text}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{OFF_WHITE};">
    <tr><td align="center" style="padding:24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;border:1px solid rgba(0,0,0,0.06);">
        <tr><td bgcolor="{DARK}" style="background-color:{DARK};padding:20px 24px;">
          <p style="margin:0;color:#FFFFFF;font-size:12px;letter-spacing:4px;text-transform:uppercase;font-weight:700;">{_escape(business)}</p>
        </td></tr>
        <tr><td style="padding:32px 24px;font-size:15px;line-height:1.55;color:{BLACK};">
          {body_html}
          <p style="margin:28px 0 0 0;">
            <a href="{_escape(magic_link_url)}" style="display:inline-block;background-color:{CYAN};color:{DARK};text-decoration:none;padding:12px 24px;border-radius:999px;font-weight:600;font-size:14px;">Show my stamps</a>
          </p>
        </td></tr>
        <tr><td style="padding:20px 24px;border-top:1px solid rgba(0,0,0,0.06);font-size:12px;color:{GREY};">
          <p style="margin:0;">You're getting this because you opted in at {_escape(business)}.</p>
          <p style="margin:6px 0 0 0;">Sent via SmartTap · <a href="{_escape(opt_out_url)}" style="color:{GREY};text-decoration:underline;">Don't email me again</a></p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return RenderedEmail(
        subject=f"We miss you at {business}",
        html=html,
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
    but didn't click the review button within the nudge window (S5 Feature 2).

    Tone is the merchant's, same as reactivation: the "From" is hello@smarttap.ie
    but the copy speaks as the local business, and the footer attributes
    SmartTap so it's not deceptive. One CTA — the Google review link. No AI,
    no emojis, no exclamation marks in the subject (template design rules)."""
    business = (tenant.get("name") or "us").strip()
    customer_name = (customer.get("name") or "").strip()
    greeting = (
        f"Hey {_escape(customer_name.split(' ')[0])}," if customer_name else "Hey there,"
    )

    body_html = f"""
        <h1 style="margin:0 0 12px 0;font-size:22px;color:{BLACK};">Thanks for visiting {_escape(business)}</h1>
        <p style="margin:0 0 12px 0;">{greeting}</p>
        <p style="margin:0 0 12px 0;">Thanks for stopping by <strong>{_escape(business)}</strong>. If you enjoyed your visit, a quick Google review means the world to a small local business — it takes under a minute.</p>
        <p style="margin:0 0 12px 0;">Tap the button below to leave one.</p>
    """

    text = (
        f"Thanks for visiting {business}\n\n"
        f"If you enjoyed your visit, a quick Google review means the world to a "
        f"small local business — it takes under a minute.\n\n"
        f"Leave a review: {review_url}\n\n"
        f"Don't email me again: {opt_out_url}\n"
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{_escape(business)}</title>
</head>
<body style="margin:0;padding:0;background-color:{OFF_WHITE};font-family:'DM Sans',Helvetica,Arial,sans-serif;color:{BLACK};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">A quick Google review for {_escape(business)} takes under a minute.</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{OFF_WHITE};">
    <tr><td align="center" style="padding:24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;border:1px solid rgba(0,0,0,0.06);">
        <tr><td bgcolor="{DARK}" style="background-color:{DARK};padding:20px 24px;">
          <p style="margin:0;color:#FFFFFF;font-size:12px;letter-spacing:4px;text-transform:uppercase;font-weight:700;">{_escape(business)}</p>
        </td></tr>
        <tr><td style="padding:32px 24px;font-size:15px;line-height:1.55;color:{BLACK};">
          {body_html}
          <p style="margin:28px 0 0 0;">
            <a href="{_escape(review_url)}" style="display:inline-block;background-color:{CYAN};color:{DARK};text-decoration:none;padding:12px 24px;border-radius:999px;font-weight:600;font-size:14px;">Leave a review</a>
          </p>
        </td></tr>
        <tr><td style="padding:20px 24px;border-top:1px solid rgba(0,0,0,0.06);font-size:12px;color:{GREY};">
          <p style="margin:0;">You're getting this because you opted in at {_escape(business)}.</p>
          <p style="margin:6px 0 0 0;">Sent via SmartTap · <a href="{_escape(opt_out_url)}" style="color:{GREY};text-decoration:underline;">Don't email me again</a></p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return RenderedEmail(
        subject=f"Thanks for visiting {business}",
        html=html,
        text=text,
    )


def whatsapp_otp_email(*, code: str) -> RenderedEmail:
    """One-time code emailed to an owner who's linking their WhatsApp number to
    the bot (S5 Feature 1). Owner-facing, so the shared footer fits — but there
    is no link CTA: the action is reading the code, so we hand-roll a shell
    with the code shown prominently. Code is digits only; safe to interpolate."""
    safe_code = _escape(str(code))
    body_html = f"""
        <h1 style="margin:0 0 12px 0;font-size:22px;color:{BLACK};">Your WhatsApp verification code</h1>
        <p style="margin:0 0 12px 0;">Hi there,</p>
        <p style="margin:0 0 16px 0;">Use this code in WhatsApp to link your number to your SmartTap account:</p>
        <p style="margin:0 0 16px 0;"><span bgcolor="{DARK}" style="display:inline-block;background-color:{DARK};color:{CYAN};font-size:30px;font-weight:700;letter-spacing:8px;padding:12px 20px;border-radius:10px;">{safe_code}</span></p>
        <p style="margin:0 0 12px 0;color:{GREY};font-size:13px;">This code expires in 10 minutes. If you didn't request it, you can ignore this email.</p>
    """
    text = (
        "Your WhatsApp verification code\n\n"
        f"Use this code in WhatsApp to link your number: {code}\n\n"
        "It expires in 10 minutes. If you didn't request it, ignore this email.\n"
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>SmartTap</title>
</head>
<body style="margin:0;padding:0;background-color:{OFF_WHITE};font-family:'DM Sans',Helvetica,Arial,sans-serif;color:{BLACK};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">Your SmartTap WhatsApp code expires in 10 minutes.</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{OFF_WHITE};">
    <tr><td align="center" style="padding:24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;border:1px solid rgba(0,0,0,0.06);">
        <tr><td bgcolor="{DARK}" style="background-color:{DARK};padding:20px 24px;">
          <p style="margin:0;color:{CYAN};font-size:12px;letter-spacing:4px;text-transform:uppercase;font-weight:700;">SmartTap</p>
        </td></tr>
        <tr><td style="padding:32px 24px;font-size:15px;line-height:1.55;color:{BLACK};">
          {body_html}
        </td></tr>
        <tr><td style="padding:20px 24px;border-top:1px solid rgba(0,0,0,0.06);font-size:12px;color:{GREY};">
          <p style="margin:0;">SmartTap · Dublin, Ireland</p>
          <p style="margin:6px 0 0 0;">You're receiving this because you signed up as the owner of a SmartTap account.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return RenderedEmail(
        subject="Your SmartTap WhatsApp code",
        html=html,
        text=text,
    )


def monthly_report_email(
    *, tenant: dict[str, Any], year: int, month: int
) -> RenderedEmail:
    """Sent on the 1st of each Dublin month with the previous month's PDF.

    Subject reads "Your SmartTap report — May 2026"; body keeps it short
    because the value is in the attachment, not the copy. The CTA points
    back to the dashboard where the merchant can re-download or look at
    today's live numbers.
    """
    import calendar

    business = (tenant.get("name") or "your business").strip()
    month_name = calendar.month_name[month] if 1 <= month <= 12 else str(month)
    period_label = f"{month_name} {year}"

    body_html = f"""
        <h1 style="margin:0 0 12px 0;font-size:22px;color:{BLACK};">Your {_escape(period_label)} report</h1>
        <p style="margin:0 0 12px 0;">{_greeting(tenant)}</p>
        <p style="margin:0 0 12px 0;">Your monthly SmartTap report for <strong>{_escape(business)}</strong> is attached as a PDF. Inside you'll find new customers, taps, stamps and rewards for {_escape(period_label)}, with comparisons to the previous month.</p>
        <p style="margin:0 0 12px 0;">Open the dashboard for today's live numbers and to schedule campaigns for the coming month.</p>
    """

    text = (
        f"Your {period_label} SmartTap report\n\n"
        f"Hi there,\n\n"
        f"Your monthly report for {business} is attached as a PDF — new customers, taps, stamps and rewards for {period_label}.\n\n"
        f"Open the dashboard: {SITE_URL}/dashboard"
    )

    return RenderedEmail(
        subject=f"Your SmartTap report — {period_label}",
        html=_layout(
            preheader=f"PDF attached — {business} for {period_label}.",
            body_html=body_html,
            cta_label="Open dashboard",
            cta_url=f"{SITE_URL}/dashboard",
        ),
        text=text,
    )


def subscription_canceled_email(*, tenant: dict[str, Any]) -> RenderedEmail:
    body_html = f"""
        <h1 style="margin:0 0 12px 0;font-size:22px;color:{BLACK};">Your subscription was canceled</h1>
        <p style="margin:0 0 12px 0;">{_greeting(tenant)}</p>
        <p style="margin:0 0 12px 0;">We've confirmed the cancellation of your SmartTap subscription. Your data stays safe — nothing is deleted — and your NFC tags will keep working for your customers.</p>
        <p style="margin:0 0 12px 0;">If you change your mind, you can resubscribe in one click any time.</p>
    """
    text = (
        "Your SmartTap subscription was canceled\n\n"
        "We've confirmed the cancellation. Your data stays safe and your NFC tags keep working for your customers.\n\n"
        f"Resubscribe any time: {SITE_URL}/dashboard/billing"
    )
    return RenderedEmail(
        subject="Your SmartTap subscription was canceled",
        html=_layout(
            preheader="Cancellation confirmed. Your data and NFC tags stay live.",
            body_html=body_html,
            cta_label="Resubscribe",
            cta_url=f"{SITE_URL}/dashboard/billing",
        ),
        text=text,
    )


# ---------------------------------------------------------------------------
# Helpers
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


# Re-exported to discourage import sprawl across the email_service.
__all__ = [
    "SITE_URL",
    "RenderedEmail",
    "monthly_report_email",
    "payment_failed_email",
    "payment_succeeded_email",
    "subscription_canceled_email",
    "welcome_email",
]
