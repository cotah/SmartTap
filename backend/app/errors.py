class BusinessError(Exception):
    """Base for domain-level errors mapped to HTTP responses in routers."""

    status_code: int = 400
    code: str = "business_error"

    def __init__(self, message: str, *, detail: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NotFoundError(BusinessError):
    status_code = 404
    code = "not_found"


class InactiveError(BusinessError):
    status_code = 410
    code = "inactive"


class RateLimitError(BusinessError):
    status_code = 429
    code = "rate_limited"


class AlreadyRedeemedError(BusinessError):
    status_code = 409
    code = "already_redeemed"


class ExpiredError(BusinessError):
    status_code = 410
    code = "expired"


class InvalidCodeError(BusinessError):
    status_code = 422
    code = "invalid_code"


class TrialExpiredError(BusinessError):
    """Trial period ended and tenant hasn't subscribed yet.

    402 (Payment Required) is the semantically correct status here — Stripe
    itself uses it for similar scenarios and most HTTP clients pass it through
    unchanged (vs the more aggressive 403 which can trigger logout flows).
    """

    status_code = 402
    code = "trial_expired"


class SubscriptionInactiveError(BusinessError):
    """Tenant had a subscription but it was canceled / payment definitively
    failed. Same 402 treatment — they need to re-subscribe to mutate."""

    status_code = 402
    code = "subscription_inactive"
