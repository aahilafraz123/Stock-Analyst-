"""Typed errors that map to meaningful HTTP responses instead of bare 500s."""

import logging

log = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, source: str | None = None):
        super().__init__(message)
        self.message = message
        self.source = source

    def to_dict(self) -> dict:
        body = {"error": self.code, "detail": self.message}
        if self.source:
            body["source"] = self.source
        return body


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class InvalidInputError(AppError):
    status_code = 422
    code = "invalid_input"


class ConfigError(AppError):
    """A required API key or setting is missing."""

    status_code = 503
    code = "not_configured"


class UpstreamError(AppError):
    """A third-party data source failed or is unreachable."""

    status_code = 502
    code = "upstream_error"


class LLMError(AppError):
    status_code = 502
    code = "llm_error"


_NETWORK_ERROR_NAMES = {
    "ConnectionError",
    "ProxyError",
    "ConnectTimeout",
    "ReadTimeout",
    "Timeout",
    "TimeoutException",
    "ConnectError",
    "RequestException",
    "CurlError",
    "HTTPError",
    "YFRateLimitError",
}


def as_app_error(exc: Exception, source: str | None = None) -> AppError:
    """Normalise arbitrary exceptions (requests/httpx/curl_cffi/yfinance) into AppErrors."""
    if isinstance(exc, AppError):
        return exc
    names = {cls.__name__ for cls in type(exc).__mro__}
    if names & _NETWORK_ERROR_NAMES:
        return UpstreamError(f"{source or 'Upstream source'} is unreachable: {exc}", source=source)
    return AppError(f"{type(exc).__name__}: {exc}", source=source)
