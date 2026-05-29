from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="http://localhost:3000")

    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    supabase_service_role_key: str = Field(default="")
    supabase_jwt_secret: str = Field(default="")

    stripe_secret_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    # Recurring monthly prices
    stripe_price_review: str = Field(default="")
    stripe_price_loyalty: str = Field(default="")
    stripe_price_pro: str = Field(default="")
    stripe_price_network: str = Field(default="")
    # One-time setup fees (added to first invoice on checkout)
    stripe_price_review_setup: str = Field(default="")
    stripe_price_loyalty_setup: str = Field(default="")
    stripe_price_pro_setup: str = Field(default="")
    stripe_price_network_setup: str = Field(default="")

    resend_api_key: str = Field(default="")
    resend_from_email: str = Field(default="hello@smarttap.ie")

    # S5 Feature 1 — WhatsApp bot via Meta WhatsApp Business Cloud API (direct,
    # no Twilio). Empty values keep the integration disabled (client no-ops,
    # like resend) so dev/CI run without credentials.
    whatsapp_access_token: str = Field(default="")  # Bearer token (system user/app)
    whatsapp_phone_number_id: str = Field(default="")  # number id on the Cloud API
    whatsapp_app_secret: str = Field(default="")  # validates X-Hub-Signature-256
    whatsapp_verify_token: str = Field(default="")  # our secret for the GET handshake
    whatsapp_api_version: str = Field(default="v21.0")
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-sonnet-4-6")

    # S5 Feature 3 — Google Business Profile (reviews). Empty values keep the
    # integration disabled (client no-ops) so dev/CI run without a Google app.
    # The Business Profile API is access-gated; build-to-activate.
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    google_oauth_redirect: str = Field(default="")  # e.g. https://api.smarttap.ie/v1/google/callback

    sentry_dsn: str = Field(default="")

    # Shared secret for the daily cron HTTP trigger. Empty disables the cron
    # endpoint entirely (returns 503), which is the safe default for envs
    # that don't have a scheduler wired up yet.
    cron_token: str = Field(default="")

    # Public origin used to build links inside transactional emails. Same
    # value as NEXT_PUBLIC_SITE_URL on the frontend; kept here so backend
    # never has to depend on frontend env files.
    site_url: str = Field(default="https://smarttap.ie")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
