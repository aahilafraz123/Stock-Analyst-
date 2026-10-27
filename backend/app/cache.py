"""Two-level TTL cache (in-process dict + SQLite) with single-flight de-duplication.

Every external fetch in this app is slow and rate limited (Yahoo, SEC, Finnhub),
and one analysis used to call `yf.Ticker(t).info` ~16 times. Decorating the
fetchers means concurrent callers for the same key share one request, results
survive restarts, and immutable data (filed SEC documents) is fetched once.

Values must be JSON-serialisable. `None` results are never cached, so a
transient failure is retried on the next call.
"""

import asyncio
import functools
import hashlib
import inspect
import json
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from app import db
from app.config import settings

log = logging.getLogger(__name__)

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR

db.register_schema(
    """
    CREATE TABLE IF NOT EXISTS cache (
        key        TEXT PRIMARY KEY,
        value      TEXT NOT NULL,
        expires_at REAL NOT NULL
    );
    """
)

_MEMORY_LIMIT = 512
_memory: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()
_memory_lock = threading.Lock()
_key_locks: dict[str, threading.Lock] = {}
_key_locks_guard = threading.Lock()
_async_locks: dict[str, asyncio.Lock] = {}
# Failures are remembered briefly so callers queued behind a failing fetch (e.g. four
# sources sharing one Yahoo quote) fail fast instead of each retrying an outage.
NEGATIVE_TTL = 20.0
_errors: dict[str, tuple[float, BaseException]] = {}


def _recent_error(key: str) -> BaseException | None:
    hit = _errors.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    return None


def _make_key(namespace: str, args: tuple, kwargs: dict) -> str:
    raw = json.dumps([args, sorted(kwargs.items())], default=str, sort_keys=True)
    digest = hashlib.sha1(raw.encode()).hexdigest()[:16]
    return f"{namespace}:{digest}"


def get(key: str) -> Any | None:
    now = time.time()
    with _memory_lock:
        hit = _memory.get(key)
        if hit and hit[0] > now:
            _memory.move_to_end(key)
            return hit[1]
    row = db.connect().execute("SELECT value, expires_at FROM cache WHERE key = ?", (key,)).fetchone()
    if row and row["expires_at"] > now:
        value = json.loads(row["value"])
        _remember(key, value, row["expires_at"])
        return value
    return None


def set(key: str, value: Any, ttl: float) -> None:
    expires_at = time.time() + ttl
    payload = json.dumps(value, default=str)
    conn = db.connect()
    conn.execute(
        "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
        (key, payload, expires_at),
    )
    conn.commit()
    # Round-trip through JSON so memory and disk hits return identical shapes.
    _remember(key, json.loads(payload), expires_at)


def _remember(key: str, value: Any, expires_at: float) -> None:
    with _memory_lock:
        _memory[key] = (expires_at, value)
        _memory.move_to_end(key)
        while len(_memory) > _MEMORY_LIMIT:
            _memory.popitem(last=False)


def clear_memory() -> None:
    with _memory_lock:
        _memory.clear()
    _errors.clear()


def _key_lock(key: str) -> threading.Lock:
    with _key_locks_guard:
        return _key_locks.setdefault(key, threading.Lock())


def cached(namespace: str, ttl: float) -> Callable:
    """Cache a sync or async function's JSON-serialisable result for `ttl` seconds."""

    def decorator(fn: Callable) -> Callable:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                if not settings.cache_enabled:
                    return await fn(*args, **kwargs)
                key = _make_key(namespace, args, kwargs)
                if (hit := get(key)) is not None:
                    return hit
                lock = _async_locks.setdefault(key, asyncio.Lock())
                async with lock:
                    if (hit := get(key)) is not None:
                        return hit
                    if err := _recent_error(key):
                        raise err
                    try:
                        value = await fn(*args, **kwargs)
                    except Exception as exc:
                        _errors[key] = (time.time() + NEGATIVE_TTL, exc)
                        raise
                    if value is not None:
                        set(key, value, ttl)
                    return get(key) if value is not None else None

            return async_wrapper

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not settings.cache_enabled:
                return fn(*args, **kwargs)
            key = _make_key(namespace, args, kwargs)
            if (hit := get(key)) is not None:
                return hit
            with _key_lock(key):
                if (hit := get(key)) is not None:
                    return hit
                if err := _recent_error(key):
                    raise err
                try:
                    value = fn(*args, **kwargs)
                except Exception as exc:
                    _errors[key] = (time.time() + NEGATIVE_TTL, exc)
                    raise
                if value is not None:
                    set(key, value, ttl)
                    return get(key)
                return None

        return wrapper

    return decorator
