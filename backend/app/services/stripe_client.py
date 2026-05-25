import stripe

from app.config import get_settings


def configure_stripe() -> None:
    settings = get_settings()
    if settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key
