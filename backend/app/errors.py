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
