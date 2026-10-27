"""The analysis pipeline: gather sources -> index documents -> retrieve evidence -> Claude -> validate.

Every piece of evidence handed to Claude gets a short ID ([F3], [N1], ...).
Claude must cite those IDs for each claim; IDs it invents are stripped and
counted, and the share of claims that keep a valid citation is reported as
`groundedness`.
"""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app import llm
from app.config import settings
from app.errors import AppError, ConfigError, NotFoundError, UpstreamError, as_app_error
from app.rag import retriever
from app.rag.embeddings import get_embedder
from app.rag.ingest import filing_doc_id, ingest_filing, ingest_transcript, transcript_doc_id
from app.rag.store import SECTION_TITLES
from app.schemas import AnalysisReport
from app.services import edgar, history, insider, institutional, market_data, news, transcripts

log = logging.getLogger(__name__)

Emit = Callable[[dict], Awaitable[None]]

# Retrieval queries used to pull targeted filing/transcript passages for the report.
TOPICS = {
    "risks": "principal risk factors uncertainties regulation litigation supply chain",
    "growth": "revenue growth drivers demand segment performance new products services",
    "margins": "gross margin operating expenses profitability cost pressures pricing",
    "liquidity": "liquidity capital resources cash flow operations debt share repurchases dividends",
    "guidance": "outlook guidance expect next quarter fiscal year forecast",
    "competition": "competition competitive position market share competitors",
}
CHUNKS_PER_TOPIC = 3
SOURCE_TIMEOUT = 60  # seconds; a hung source degrades to "error" instead of stalling the report


@dataclass
class Source:
    name: str
    label: str
    fetch: Callable[[], Awaitable[Any]]
    status: str = "pending"
    ms: int = 0
    detail: str | None = None
    value: Any = None
    exc: AppError | None = None


@dataclass
class EvidenceBook:
    """Numbered evidence blocks shown to Claude and returned to the UI as citations."""

    items: list[dict] = field(default_factory=list)
    _counters: dict[str, int] = field(default_factory=dict)

    def add(
        self, prefix: str, kind: str, label: str, text: str, url: str | None = None, date: str | None = None
    ) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        sid = f"{prefix}{self._counters[prefix]}"
        self.items.append({"id": sid, "kind": kind, "label": label, "url": url, "date": date, "text": text})
        return sid

    def ids(self) -> set[str]:
        return {i["id"] for i in self.items}

    def render(self) -> str:
        blocks = []
        for i in self.items:
            attrs = f'id="{i["id"]}" kind="{i["kind"]}" label="{i["label"]}"'
            if i["date"]:
                attrs += f' date="{i["date"]}"'
            blocks.append(f"<source {attrs}>\n{i['text']}\n</source>")
        return "\n\n".join(blocks)

    def public(self) -> list[dict]:
        return [{k: v for k, v in i.items() if k != "text"} | {"excerpt": i["text"][:400]} for i in self.items]


def _thread(fn, *args, **kwargs) -> Callable[[], Awaitable[Any]]:
    return lambda: asyncio.to_thread(fn, *args, **kwargs)


def _sources(ticker: str) -> list[Source]:
    return [
        Source("profile", "Company profile", _thread(market_data.get_company_profile, ticker)),
        Source("ratios", "Financial ratios", _thread(market_data.get_financial_ratios, ticker)),
        Source("price", "Price momentum", _thread(market_data.get_price_context, ticker)),
        Source("analysts", "Analyst consensus", _thread(market_data.get_analyst_consensus, ticker)),
        Source("peers", "Peer comparison", _thread(market_data.get_competitor_ratios, ticker)),
        Source("filing_10k", "10-K annual report", _thread(edgar.get_filing, ticker, "10-K", 0)),
        Source("filing_10q", "10-Q quarterly report", _thread(edgar.get_filing, ticker, "10-Q", 0)),
        Source("transcript", "Earnings call transcript", _thread(transcripts.get_latest_earnings_transcript, ticker)),
        Source("insider", "Insider trades", _thread(insider.get_insider_trades, ticker)),
        Source("institutional", "Institutional ownership", _thread(institutional.get_institutional_ownership, ticker)),
        Source("news", "News (14 days)", lambda: news.get_company_news(ticker, days_back=14, limit=10)),
        Source("sentiment", "News sentiment", lambda: news.get_company_sentiment(ticker)),
        Source("benchmark", "S&P 500 benchmark", _thread(market_data.get_info, history.BENCHMARK)),
    ]


async def _noop(_: dict) -> None:
    return None


def _failure_status(err: AppError) -> str:
    if isinstance(err, ConfigError):
        return "skipped"  # no API key configured for this source
    if isinstance(err, NotFoundError):
        return "empty"  # e.g. no earnings calls for a recent IPO
    return "error"


async def gather_sources(ticker: str, emit: Emit) -> dict[str, Source]:
    sources = _sources(ticker)

    async def run(src: Source) -> None:
        started = time.perf_counter()
        try:
            src.value = await asyncio.wait_for(src.fetch(), SOURCE_TIMEOUT)
            src.status = "ok" if src.value not in (None, [], {}) else "empty"
        except Exception as exc:
            if isinstance(exc, TimeoutError):
                exc = UpstreamError(f"{src.label} timed out after {SOURCE_TIMEOUT}s", source=src.label)
            err = as_app_error(exc, src.label)
            src.status = _failure_status(err)
            src.detail = err.message[:300]
            src.exc = err
        src.ms = int((time.perf_counter() - started) * 1000)
        await emit(
            {
                "type": "source",
                "name": src.name,
                "label": src.label,
                "status": src.status,
                "ms": src.ms,
                "detail": src.detail,
            }
        )

    for src in sources:
        await emit({"type": "source", "name": src.name, "label": src.label, "status": "pending"})
    await asyncio.gather(*(run(s) for s in sources))
    return {s.name: s for s in sources}


def _index_documents(filings: list[dict], transcript: dict | None) -> list[str]:
    doc_ids = []
    for filing in filings:
        try:
            ingest_filing(filing)
            doc_ids.append(filing_doc_id(filing))
        except Exception as exc:
            log.warning("Indexing %s failed: %s", filing.get("accessionNumber"), exc)
    if transcript:
        try:
            ingest_transcript(transcript)
            doc_ids.append(transcript_doc_id(transcript))
        except Exception as exc:
            log.warning("Indexing transcript failed: %s", exc)
    return doc_ids


def _compact(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"), default=str)


def build_evidence(ticker: str, s: dict[str, Source], hits: dict[str, list]) -> EvidenceBook:
    book = EvidenceBook()
    v = {name: src.value for name, src in s.items() if src.status == "ok"}

    if "profile" in v:
        profile = dict(v["profile"])
        profile["description"] = (profile.get("description") or "")[:1200]
        book.add(
            "M",
            "market",
            "Company profile & fundamentals (Yahoo Finance)",
            _compact({"profile": profile, "ratios": v.get("ratios")}),
        )
    if "price" in v:
        book.add("M", "market", "Price momentum & 52-week range (Yahoo Finance)", _compact(v["price"]))
    if "analysts" in v:
        book.add("A", "analysts", "Wall Street consensus & price targets", _compact(v["analysts"]))
    if "peers" in v:
        book.add("P", "peers", "Peer valuation & profitability comparison", _compact(v["peers"]))
    if "insider" in v:
        ins = v["insider"]
        book.add(
            "I",
            "insider",
            "Insider transactions (Form 4)",
            f"Summary: {ins.get('summary')}\nRecent: {_compact(ins.get('trades', [])[:8])}",
        )
    if "institutional" in v:
        inst = v["institutional"]
        book.add(
            "O",
            "ownership",
            "Institutional ownership (13F)",
            f"Summary: {inst.get('summary')}\nTop holders: {_compact(inst.get('topInstitutions', [])[:6])}",
        )
    if "sentiment" in v:
        book.add("S", "sentiment", "News sentiment scores (Finnhub)", _compact(v["sentiment"]))

    for topic_hits in hits.values():
        for h in topic_hits:
            prefix = "T" if h.kind == "transcript" else "F"
            label = f"{h.title} · {SECTION_TITLES.get(h.section, h.section)}"
            book.add(prefix, h.form, label, h.text, url=h.url, date=h.filed)

    if not any(i["id"].startswith("F") for i in book.items):
        # Retrieval unavailable: fall back to the head of each extracted section.
        for name in ("filing_10q", "filing_10k"):
            if name in v:
                f = v[name]
                for key in ("mda", "risk_factors"):
                    if text := f["sections"].get(key):
                        book.add(
                            "F",
                            f["form"],
                            f"{ticker} {f['form']} · {SECTION_TITLES[key]}",
                            text[:6000],
                            url=f["url"],
                            date=f["filingDate"],
                        )

    for item in v.get("news", [])[:10]:
        body = (item.get("body") or item.get("summary") or "")[:1500]
        book.add(
            "N",
            "news",
            f"{item.get('headline')} ({item.get('source')})",
            body,
            url=item.get("url"),
            date=item.get("datetime"),
        )
    return book


SYSTEM_PROMPT = """You are a senior equity research analyst writing an institutional-quality report.

Ground every statement in the evidence provided. Each <source> block has an id such as F3 or N1. For every
claim, list the ids of the sources that support it in its `sources` field. Use only ids that appear in the
evidence; if no source supports a point, leave it out rather than guessing. Quote specific figures (growth
rates, margins, multiples, price targets) where the evidence has them.

Weigh the evidence the way a skeptical analyst would: management's prepared remarks against the analyst Q&A,
the 10-K risk factors against recent news, the valuation against peers and growth. Take a clear position,
and set confidenceScore to reflect how complete and consistent the evidence is (missing sources or
conflicting signals mean lower confidence). If a source category is absent, do not pretend otherwise."""


def _validate_citations(report: AnalysisReport, valid: set[str]) -> dict:
    total = removed = grounded = claims = 0

    def clean(obj) -> None:
        nonlocal total, removed, grounded, claims
        before = list(obj.sources)
        obj.sources = [sid for sid in before if sid in valid]
        total += len(before)
        removed += len(before) - len(obj.sources)
        claims += 1
        grounded += bool(obj.sources)

    for name in (
        "summary",
        "valuation",
        "financialHealth",
        "competitivePosition",
        "managementTone",
        "recentNewsImpact",
        "priceContext",
        "analystConsensus",
        "recommendationReasoning",
    ):
        clean(getattr(report, name))
    for name in ("strengths", "risks", "catalysts"):
        for claim in getattr(report, name):
            clean(claim)
    report.confidenceScore = max(0, min(100, report.confidenceScore))
    return {
        "total": total,
        "invalidRemoved": removed,
        "claims": claims,
        "groundedClaims": grounded,
        "groundedness": round(grounded / claims, 3) if claims else None,
    }


async def run_analysis(ticker: str, emit: Emit | None = None, refresh: bool = False) -> dict:
    emit = emit or _noop
    started = time.perf_counter()

    if not refresh and (cached := history.latest(ticker, settings.report_ttl_seconds)):
        cached["meta"]["cached"] = True
        await emit({"type": "stage", "stage": "cached", "message": "Serving a recent report"})
        return cached

    await emit({"type": "stage", "stage": "sources", "message": "Fetching data sources in parallel"})
    s = await gather_sources(ticker, emit)
    profile = s["profile"]
    if profile.status != "ok":
        raise profile.exc or NotFoundError(f"Ticker {ticker} not found")

    await emit({"type": "stage", "stage": "indexing", "message": "Indexing filings & transcript for retrieval"})
    filings = [s[n].value for n in ("filing_10k", "filing_10q") if s[n].status == "ok"]
    transcript = s["transcript"].value if s["transcript"].status == "ok" else None
    doc_ids = await asyncio.to_thread(_index_documents, filings, transcript)

    await emit({"type": "stage", "stage": "retrieval", "message": "Retrieving evidence by topic"})
    hits = await asyncio.to_thread(retriever.multi_search, ticker, TOPICS, CHUNKS_PER_TOPIC, doc_ids) if doc_ids else {}
    book = build_evidence(ticker, s, hits)

    await emit({"type": "stage", "stage": "llm", "message": f"Writing the report with {settings.anthropic_model}"})
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    prompt = (
        f"Today is {today}. Write the research report for {ticker} "
        f"({profile.value.get('companyName')}).\n\n<evidence>\n{book.render()}\n</evidence>"
    )

    async def llm_progress(update: dict) -> None:
        await emit({"type": "llm", **update})

    report, usage = await llm.structured(SYSTEM_PROMPT, prompt, AnalysisReport, on_progress=llm_progress)
    citations = _validate_citations(report, book.ids())

    analysts = s["analysts"].value if s["analysts"].status == "ok" else {}
    benchmark = s["benchmark"].value if s["benchmark"].status == "ok" else None
    embedder = get_embedder()
    response = {
        "ticker": ticker,
        "companyName": profile.value.get("companyName"),
        "analysisDate": today,
        "generatedAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "report": report.model_dump(),
        "sources": book.public(),
        "metrics": {
            "currentPrice": profile.value.get("currentPrice"),
            "targetMeanPrice": analysts.get("targetMeanPrice"),
            "impliedUpsidePct": analysts.get("impliedUpsidePct"),
            "numberOfAnalysts": analysts.get("numberOfAnalysts"),
        },
        "meta": {
            **usage,
            "cached": False,
            "totalLatencyMs": int((time.perf_counter() - started) * 1000),
            "benchmarkPrice": market_data.current_price(benchmark) if benchmark else None,
            "sourceStatus": [
                {"name": x.name, "label": x.label, "status": x.status, "ms": x.ms, "detail": x.detail}
                for x in s.values()
            ],
            "retrieval": {
                "mode": "hybrid" if embedder else "bm25",
                "embedder": embedder.name if embedder else None,
                "documents": doc_ids,
                "chunks": sum(len(h) for h in hits.values()),
            },
            "citations": citations,
        },
    }
    response["meta"]["reportId"] = await asyncio.to_thread(history.save, response)
    log.info(
        "[%s] report done in %dms (%s in / %s out tokens, groundedness %s)",
        ticker,
        response["meta"]["totalLatencyMs"],
        usage["inputTokens"],
        usage["outputTokens"],
        citations["groundedness"],
    )
    return response


async def stream_analysis(ticker: str, refresh: bool = False):
    """Yield pipeline events as dicts; the last one is `report` or `error`."""
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: dict) -> None:
        await queue.put(event)

    async def runner() -> None:
        try:
            result = await run_analysis(ticker, emit, refresh=refresh)
            await queue.put({"type": "report", "data": result})
        except Exception as exc:
            if not isinstance(exc, AppError):
                log.exception("[%s] analysis failed", ticker)
            err = as_app_error(exc)
            await queue.put({"type": "error", "status": err.status_code, **err.to_dict()})
        finally:
            await queue.put(None)

    task = asyncio.create_task(runner())
    try:
        while (event := await queue.get()) is not None:
            yield event
    finally:
        if not task.done():
            task.cancel()
