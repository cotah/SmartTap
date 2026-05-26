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
