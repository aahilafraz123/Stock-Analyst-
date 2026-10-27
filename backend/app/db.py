"""Single SQLite database backing the cache, the retrieval index and report history.

SQLite keeps the project zero-infrastructure: one file, no server, WAL mode for
concurrent readers. Each thread gets its own connection.
"""

import sqlite3
import threading
from pathlib import Path

from app.config import settings

_SCHEMA: list[str] = []
_local = threading.local()
_init_lock = threading.Lock()
_applied: dict[Path, int] = {}  # path -> number of registered DDL scripts already applied


def register_schema(ddl: str) -> None:
    """Modules register their tables at import time; applied on first connect."""
    _SCHEMA.append(ddl)


def _open(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _initialise(path: Path) -> None:
    # Switching to WAL and running DDL need an exclusive lock, and SQLite reports
    # "database is locked" immediately (no busy wait) when several threads try it at
    # once, as the 13 parallel source fetches do on a fresh database. Do it once.
    if _applied.get(path) == len(_SCHEMA):  # lock-free fast path
        return
    with _init_lock:
        done = _applied.get(path, 0)
        if done == len(_SCHEMA):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = _open(path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")  # persistent: stored in the file
            for ddl in _SCHEMA[done:]:
                conn.executescript(ddl)
        finally:
            conn.close()
        _applied[path] = len(_SCHEMA)


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = Path(path or settings.db_path)
    cached = getattr(_local, "conns", None)
    if cached is None:
        cached = _local.conns = {}
    _initialise(path)  # no-op once the file is set up (and picks up late-registered tables)
    conn = cached.get(path)
    if conn is None:
        conn = cached[path] = _open(path)
    return conn
