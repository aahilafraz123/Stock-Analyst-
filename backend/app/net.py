"""Shared HTTP plumbing: pooled sessions, timeouts, retries and SEC rate limiting."""

import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import settings
from app.errors import NotFoundError, UpstreamError

DEFAULT_TIMEOUT = (5, 30)  # (connect, read) seconds


class _Throttle:
    """Simple process-wide rate limiter. SEC allows at most 10 requests/second."""

    def __init__(self, per_second: float):
        self.interval = 1.0 / per_second
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + self.interval
        if delay > 0:
            time.sleep(delay)


def _session(user_agent: str | None = None) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if user_agent:
        session.headers["User-Agent"] = user_agent
    return session


_sec_session = _session(settings.sec_user_agent)
_sec_session.headers["Accept-Encoding"] = "gzip, deflate"
_sec_throttle = _Throttle(per_second=8)


def sec_get(url: str, timeout=DEFAULT_TIMEOUT) -> requests.Response:
    _sec_throttle.wait()
    try:
        response = _sec_session.get(url, timeout=timeout)
    except requests.RequestException as exc:
        raise UpstreamError(f"SEC EDGAR is unreachable: {exc}", source="SEC EDGAR") from exc
    if response.status_code == 404:
        raise NotFoundError(f"SEC document not found: {url}", source="SEC EDGAR")
    if response.status_code >= 400:
        raise UpstreamError(f"SEC EDGAR returned HTTP {response.status_code} for {url}", source="SEC EDGAR")
    return response
