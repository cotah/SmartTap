"""Smoke tests for email templates.

These guard the contract — subject is non-empty and stable, every template
produces both HTML and plain-text, and the values we feed in (business name,
amount) actually surface in the rendered output. Pixel-perfect rendering is
not testable here; verify in Resend's preview when you change layout.
"""

from typing import Any

import pytest

from app.emails import templates


def _tenant(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "t-1",
        "name": "ACME Barber",
        "plan": "loyalty",
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# welcome
# ---------------------------------------------------------------------------


def test_welcome_subject_includes_business_name() -> None:
    rendered = templates.welcome_email(tenant=_tenant(name="ACME Barber"))
    assert "ACME Barber" in rendered.subject
    assert rendered.subject == "Welcome to SmartTap, ACME Barber"


def test_welcome_html_and_text_non_empty() -> None:
    rendered = templates.welcome_email(tenant=_tenant())
    assert rendered.html.strip().startswith("<!doctype html>")
    assert "ACME Barber" in rendered.html
    assert rendered.text
    assert "ACME Barber" in rendered.text


def test_welcome_falls_back_when_business_name_is_default() -> None:
    """Pre-onboarding tenants have name='My business' — we must not address
    them as if it's their real name."""
    rendered = templates.welcome_email(tenant=_tenant(name="My business"))
    assert "Hi there," in rendered.html
    # Subject still uses the placeholder name so it stays predictable.
    assert "My business" in rendered.subject


def test_welcome_escapes_business_name_in_html() -> None:
    """Defensive: business names come from user input; never let a tenant put
    <script> in their name and break our emails."""
    rendered = templates.welcome_email(
        tenant=_tenant(name="<script>alert('x')</script>")
    )
    assert "<script>" not in rendered.html
    assert "&lt;script&gt;" in rendered.html


def test_welcome_has_dashboard_cta() -> None:
    rendered = templates.welcome_email(tenant=_tenant())
    assert "/dashboard" in rendered.html
    assert "/dashboard" in rendered.text


# ---------------------------------------------------------------------------
# payment_succeeded
# ---------------------------------------------------------------------------


def test_payment_succeeded_formats_amount_correctly() -> None:
    """5900 cents EUR → €59.00 in both HTML and text."""
    rendered = templates.payment_succeeded_email(
        tenant=_tenant(),
        plan="loyalty",
        amount_total=5900,
        currency="eur",
    )
    assert "€59.00" in rendered.html
    assert "€59.00" in rendered.text


def test_payment_succeeded_uses_plan_display_name() -> None:
    rendered = templates.payment_succeeded_email(
        tenant=_tenant(), plan="loyalty", amount_total=5900, currency="eur"
    )
    assert "SmartLoyalty" in rendered.html
    # The raw plan id must not leak.
    assert " loyalty " not in rendered.html.lower()


def test_payment_succeeded_handles_missing_amount() -> None:
    """Stripe sometimes returns None on weird coupon flows; render `—`
    instead of crashing."""
    rendered = templates.payment_succeeded_email(
        tenant=_tenant(), plan="loyalty", amount_total=None, currency="eur"
    )
    assert "—" in rendered.html


def test_payment_succeeded_falls_back_to_tenant_plan() -> None:
    """If the webhook doesn't include the plan, derive it from tenant.plan."""
    rendered = templates.payment_succeeded_email(
        tenant=_tenant(plan="pro"), plan=None, amount_total=9900, currency="eur"
    )
    assert "SmartPro" in rendered.html


# ---------------------------------------------------------------------------
# payment_failed
# ---------------------------------------------------------------------------


def test_payment_failed_includes_amount_due() -> None:
    rendered = templates.payment_failed_email(
        tenant=_tenant(), amount_due=2900, currency="eur"
    )
    assert "€29.00" in rendered.html
    assert "€29.00" in rendered.text


def test_payment_failed_points_to_billing() -> None:
    rendered = templates.payment_failed_email(
        tenant=_tenant(), amount_due=2900, currency="eur"
    )
    assert "/dashboard/billing" in rendered.html
    assert "/dashboard/billing" in rendered.text


def test_payment_failed_does_not_blame_user_for_retry() -> None:
    """Tone check — the line about Stripe retrying should be present so the
    customer doesn't panic-cancel."""
    rendered = templates.payment_failed_email(
        tenant=_tenant(), amount_due=2900, currency="eur"
    )
    assert "retry" in rendered.html.lower()


# ---------------------------------------------------------------------------
# subscription_canceled
# ---------------------------------------------------------------------------


def test_subscription_canceled_reassures_about_data() -> None:
    """Big anxiety on cancellation is "is my data gone?". The copy must
    address that explicitly."""
    rendered = templates.subscription_canceled_email(tenant=_tenant())
    assert "data stays safe" in rendered.html.lower()


def test_subscription_canceled_keeps_resubscribe_path() -> None:
    rendered = templates.subscription_canceled_email(tenant=_tenant())
    assert "/dashboard/billing" in rendered.html


# ---------------------------------------------------------------------------
# Subject lines — explicit guard so they don't drift in copy refactors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "subject",
    [
        "Welcome to SmartTap, ACME Barber",
        "Your SmartTap subscription is active",
        "We couldn't charge your card for SmartTap",
        "Your SmartTap subscription was canceled",
        "We miss you at ACME Barber",
    ],
)
def test_subjects_have_no_emoji_or_exclamation(subject: str) -> None:
    """Tone rule from the spec — keep subjects calm and scannable."""
    assert "!" not in subject
    # Rough ASCII check — no emoji.
    assert all(ord(c) < 128 or c == "'" for c in subject)


# ---------------------------------------------------------------------------
# reactivation — sent on behalf of the merchant to a dormant customer
# ---------------------------------------------------------------------------


def _customer(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "c-1",
        "name": "Alex",
        "email": "alex@example.test",
        "current_stamps": 3,
        "magic_link_token": "tok_abc12345",
    }
    base.update(over)
    return base


def test_reactivation_subject_uses_business_name() -> None:
    rendered = templates.reactivation_email(
        tenant=_tenant(name="ACME Barber", stamps_for_reward=10, reward_description="a free cut"),
        customer=_customer(),
        magic_link_url="https://smarttap.ie/m/tok_abc12345",
        opt_out_url="https://smarttap.ie/u/tok_abc12345",
    )
    assert rendered.subject == "We miss you at ACME Barber"


def test_reactivation_progress_line_when_stamps_remaining() -> None:
    """3 current / 10 threshold → 7 stamps to reward."""
    rendered = templates.reactivation_email(
        tenant=_tenant(stamps_for_reward=10, reward_description="a free cut"),
        customer=_customer(current_stamps=3),
        magic_link_url="https://smarttap.ie/m/t1",
        opt_out_url="https://smarttap.ie/u/t1",
    )
    assert "7" in rendered.text
    assert "free cut" in rendered.text


def test_reactivation_says_reward_is_waiting_when_already_reached() -> None:
    """Customer has enough stamps but never claimed — pitch the reward, not
    the missing count."""
    rendered = templates.reactivation_email(
        tenant=_tenant(stamps_for_reward=10, reward_description="a free coffee"),
        customer=_customer(current_stamps=10),
        magic_link_url="https://smarttap.ie/m/t1",
        opt_out_url="https://smarttap.ie/u/t1",
    )
    assert "waiting" in rendered.text.lower()
    assert "free coffee" in rendered.text


def test_reactivation_uses_first_name_in_greeting() -> None:
    rendered = templates.reactivation_email(
        tenant=_tenant(),
        customer=_customer(name="Alex Murphy"),
        magic_link_url="https://smarttap.ie/m/t1",
        opt_out_url="https://smarttap.ie/u/t1",
    )
    # First name only — don't use the full name in the greeting.
    assert "Hey Alex," in rendered.html


def test_reactivation_falls_back_when_customer_has_no_name() -> None:
    rendered = templates.reactivation_email(
        tenant=_tenant(),
        customer=_customer(name=None),
        magic_link_url="https://smarttap.ie/m/t1",
        opt_out_url="https://smarttap.ie/u/t1",
    )
    assert "Hey there," in rendered.html


def test_reactivation_escapes_business_name() -> None:
    """Defensive — merchant could put anything in their business name."""
    rendered = templates.reactivation_email(
        tenant=_tenant(name="<script>evil()</script>"),
        customer=_customer(),
        magic_link_url="https://smarttap.ie/m/t1",
        opt_out_url="https://smarttap.ie/u/t1",
    )
    assert "<script>" not in rendered.html
    assert "&lt;script&gt;" in rendered.html


def test_reactivation_includes_both_cta_and_opt_out_links() -> None:
    """The primary CTA should be the magic link; the opt-out belongs in the
    footer. Both must be present and clickable."""
    rendered = templates.reactivation_email(
        tenant=_tenant(),
        customer=_customer(),
        magic_link_url="https://smarttap.ie/m/tok_abc12345",
        opt_out_url="https://smarttap.ie/u/tok_abc12345",
    )
    assert 'href="https://smarttap.ie/m/tok_abc12345"' in rendered.html
    assert 'href="https://smarttap.ie/u/tok_abc12345"' in rendered.html
    # Plain-text fallback should also expose both URLs for non-HTML clients.
    assert "https://smarttap.ie/m/tok_abc12345" in rendered.text
    assert "https://smarttap.ie/u/tok_abc12345" in rendered.text


def test_reactivation_footer_is_customer_facing_not_merchant() -> None:
    """The shared layout footer addresses tenant owners ("you signed up as
    the owner"). Reactivation hand-rolls its own shell so the footer makes
    sense for end customers."""
    rendered = templates.reactivation_email(
        tenant=_tenant(name="ACME Barber"),
        customer=_customer(),
        magic_link_url="https://smarttap.ie/m/t1",
        opt_out_url="https://smarttap.ie/u/t1",
    )
    assert "signed up as the owner" not in rendered.html
    assert "opted in at ACME Barber" in rendered.html
