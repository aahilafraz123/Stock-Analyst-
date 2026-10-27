"""Persisted reports, and a scorecard of past recommendations vs. what the stock did next."""

import json
import logging
import time

from app import db
from app.services import market_data

log = logging.getLogger(__name__)

BENCHMARK = "SPY"
HOLD_BAND_PCT = 5.0  # a HOLD "hits" if the stock stays within ±5% of the benchmark

db.register_schema(
    """
    CREATE TABLE IF NOT EXISTS reports (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker          TEXT NOT NULL,
        created_at      REAL NOT NULL,
        model           TEXT,
        recommendation  TEXT,
        signal          TEXT,
        confidence      INTEGER,
        price           REAL,
        benchmark_price REAL,
        payload         TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS reports_ticker_created ON reports(ticker, created_at DESC);
    """
)


def save(response: dict) -> int:
    report = response["report"]
    conn = db.connect()
    cursor = conn.execute(
        "INSERT INTO reports (ticker, created_at, model, recommendation, signal, confidence, price,"
        " benchmark_price, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            response["ticker"],
            time.time(),
            response["meta"].get("model"),
            report["recommendation"],
            report["overallSignal"],
            report["confidenceScore"],
            response["metrics"].get("currentPrice"),
            response["meta"].get("benchmarkPrice"),
            json.dumps(response, default=str),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def latest(ticker: str, max_age_seconds: float) -> dict | None:
    row = (
        db.connect()
        .execute(
            "SELECT id, payload FROM reports WHERE ticker = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 1",
            (ticker, time.time() - max_age_seconds),
        )
        .fetchone()
    )
    if not row:
        return None
    payload = json.loads(row["payload"])
    payload["meta"]["reportId"] = row["id"]
    return payload


def get(report_id: int) -> dict | None:
    row = db.connect().execute("SELECT id, payload FROM reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        return None
    payload = json.loads(row["payload"])
    payload["meta"]["reportId"] = row["id"]
    return payload


def _summary_row(row) -> dict:
    return {
        "id": row["id"],
        "ticker": row["ticker"],
        "createdAt": row["created_at"],
        "model": row["model"],
        "recommendation": row["recommendation"],
        "signal": row["signal"],
        "confidence": row["confidence"],
        "price": row["price"],
        "benchmarkPrice": row["benchmark_price"],
    }


def list_reports(ticker: str | None = None, limit: int = 50) -> list[dict]:
    conn = db.connect()
    if ticker:
        rows = conn.execute(
            "SELECT * FROM reports WHERE ticker = ? ORDER BY created_at DESC LIMIT ?", (ticker, limit)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_summary_row(r) for r in rows]


def _price_now(ticker: str) -> float | None:
    try:
        return market_data.current_price(market_data.get_info(ticker))
    except Exception as exc:
        log.info("No current price for %s: %s", ticker, exc)
        return None


def score(recommendation: str, excess_pct: float) -> bool:
    if recommendation == "BUY":
        return excess_pct > 0
    if recommendation == "SELL":
        return excess_pct < 0
    return abs(excess_pct) <= HOLD_BAND_PCT


def track_record(min_age_days: float = 7, limit: int = 200) -> dict:
    """Return since each report vs. SPY over the same window. Reports younger than
    `min_age_days` are listed but excluded from the hit rate (too early to judge)."""
    rows = list_reports(limit=limit)
    prices = {t: _price_now(t) for t in {r["ticker"] for r in rows} | {BENCHMARK}}
    now = time.time()
    entries, scored = [], []
    for r in rows:
        current, bench_now = prices.get(r["ticker"]), prices.get(BENCHMARK)
        ret = market_data.pct_change(current, r["price"], 2) if current and r["price"] else None
        bench = market_data.pct_change(bench_now, r["benchmarkPrice"], 2) if bench_now and r["benchmarkPrice"] else None
        excess = round(ret - bench, 2) if ret is not None and bench is not None else None
        age_days = (now - r["createdAt"]) / 86400
        hit = score(r["recommendation"], excess) if excess is not None else None
        entry = {
            **r,
            "currentPrice": current,
            "returnPct": ret,
            "benchmarkReturnPct": bench,
            "excessReturnPct": excess,
            "ageDays": round(age_days, 1),
            "hit": hit,
            "matured": age_days >= min_age_days,
        }
        entries.append(entry)
        if entry["matured"] and hit is not None:
            scored.append(entry)
    hits = sum(e["hit"] for e in scored)
    return {
        "benchmark": BENCHMARK,
        "minAgeDays": min_age_days,
        "scoredReports": len(scored),
        "hitRate": round(hits / len(scored), 3) if scored else None,
        "avgExcessReturnPct": round(sum(e["excessReturnPct"] for e in scored) / len(scored), 2) if scored else None,
        "reports": entries,
    }
