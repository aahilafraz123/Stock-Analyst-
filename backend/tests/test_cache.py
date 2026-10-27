import asyncio
import threading
import time

import pytest

from app import cache


def test_caches_results_and_skips_none():
    calls = {"n": 0}

    @cache.cached("t.basic", ttl=60)
    def fetch(x):
        calls["n"] += 1
        return None if x == "missing" else {"x": x}

    assert fetch("a") == {"x": "a"}
    assert fetch("a") == {"x": "a"}
    assert calls["n"] == 1
    fetch("missing")
    fetch("missing")
    assert calls["n"] == 3  # None is never cached


def test_persists_across_memory_clear():
    calls = {"n": 0}

    @cache.cached("t.persist", ttl=60)
    def fetch():
        calls["n"] += 1
        return [1, 2, 3]

    fetch()
    cache.clear_memory()
    assert fetch() == [1, 2, 3]
    assert calls["n"] == 1  # served from SQLite


def test_expiry():
    cache.set("t.expire", {"v": 1}, ttl=0.05)
    assert cache.get("t.expire") == {"v": 1}
    time.sleep(0.1)
    assert cache.get("t.expire") is None


def test_single_flight_across_threads():
    calls = {"n": 0}

    @cache.cached("t.flight", ttl=60)
    def slow():
        calls["n"] += 1
        time.sleep(0.2)
        return {"ok": True}

    threads = [threading.Thread(target=slow) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert calls["n"] == 1


def test_failures_are_shared_briefly():
    calls = {"n": 0}

    @cache.cached("t.fail", ttl=60)
    def flaky():
        calls["n"] += 1
        raise RuntimeError("upstream down")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            flaky()
    assert calls["n"] == 1


def test_async_functions():
    calls = {"n": 0}

    @cache.cached("t.async", ttl=60)
    async def fetch(x):
        calls["n"] += 1
        await asyncio.sleep(0.01)
        return {"x": x}

    async def main():
        return await asyncio.gather(*(fetch(1) for _ in range(5)))

    assert asyncio.run(main()) == [{"x": 1}] * 5
    assert calls["n"] == 1
