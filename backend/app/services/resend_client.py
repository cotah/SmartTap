import resend

from app.config import get_settings


def configure_resend() -> None:
    settings = get_settings()
    if settings.resend_api_key:
        resend.api_key = settings.resend_api_key
