"""Company and market news from Finnhub, with article bodies fetched concurrently."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx

from app.cache import MINUTE, cached
from app.config import settings
from app.errors import ConfigError, UpstreamError

log = logging.getLogger(__name__)

SOURCE = "Finnhub"
BASE_URL = "https://finnhub.io/api/v1"
_BODY_CHARS = 4000
_BODY_CONCURRENCY = 5
_BODY_TIMEOUT = 12  # seconds per article
_BODY_BUDGET = 25  # seconds for all article bodies together


async def _finnhub(path: str, params: dict):
    if not settings.finnhub_api_key:
        raise ConfigError("FINNHUB_API_KEY is not set", source=SOURCE)
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{BASE_URL}{path}", params={**params, "token": settings.finnhub_api_key})
    except httpx.HTTPError as exc:
        raise UpstreamError(f"Finnhub is unreachable: {exc}", source=SOURCE) from exc
    if response.status_code == 401:
        raise ConfigError("Finnhub rejected FINNHUB_API_KEY", source=SOURCE)
    if response.status_code == 403:
        # Free keys get 403 on premium endpoints such as news-sentiment.
        return None
    if response.status_code >= 400:
        raise UpstreamError(f"Finnhub returned HTTP {response.status_code}", source=SOURCE)
    data = response.json()
    if isinstance(data, dict) and data.get("error"):
        return None
    return data


def _article_text(url: str) -> str:
    from newspaper import Article, Config  # heavy import; only needed here

    config = Config()
    config.request_timeout = _BODY_TIMEOUT
    config.browser_user_agent = "Mozilla/5.0 (compatible; StockAnalyzer/1.0)"
    config.fetch_images = False
    article = Article(url, config=config)
    article.download()
    article.parse()
    return (article.text or "")[:_BODY_CHARS]


async def _fetch_bodies(urls: list[str]) -> list[str]:
    semaphore = asyncio.Semaphore(_BODY_CONCURRENCY)

    async def one(url: str) -> str:
        if not url:
            return ""
        async with semaphore:
            try:
                return await asyncio.wait_for(asyncio.to_thread(_article_text, url), _BODY_TIMEOUT + 3)
            except Exception as exc:
                log.debug("Article body unavailable (%s): %s", url, exc)
                return ""

    tasks = [asyncio.create_task(one(u)) for u in urls]
    done, pending = await asyncio.wait(tasks, timeout=_BODY_BUDGET)
    for task in pending:
        task.cancel()
    return [t.result() if t in done and not t.cancelled() else "" for t in tasks]


def _iso(ts) -> str | None:
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError, OSError):
        return None


@cached("finnhub.company_news", ttl=30 * MINUTE)
async def get_company_news(ticker: str, days_back: int = 7, limit: int = 10, with_bodies: bool = True) -> list[dict]:
    today = datetime.now(UTC).date()
    data = await _finnhub(
        "/company-news",
        {"symbol": ticker, "from": str(today - timedelta(days=days_back)), "to": str(today)},
    )
    if not isinstance(data, list):
        return []
    items = sorted(data, key=lambda i: i.get("datetime", 0), reverse=True)[:limit]
    bodies = await _fetch_bodies([i.get("url", "") for i in items]) if with_bodies else [""] * len(items)
    return [
        {
            "headline": item.get("headline"),
            "summary": item.get("summary"),
            "body": body,
            "source": item.get("source"),
            "url": item.get("url"),
            "datetime": _iso(item.get("datetime")),
        }
        for item, body in zip(items, bodies, strict=True)
    ]


@cached("finnhub.market_news", ttl=15 * MINUTE)
async def get_market_news(category: str = "general") -> list[dict]:
    data = await _finnhub("/news", {"category": category})
    if not isinstance(data, list):
        return []
    return [
        {
            "headline": item.get("headline"),
            "summary": item.get("summary"),
            "source": item.get("source"),
            "url": item.get("url"),
            "datetime": _iso(item.get("datetime")),
        }
        for item in data[:20]
    ]


@cached("finnhub.sentiment", ttl=6 * 60 * MINUTE)
async def get_company_sentiment(ticker: str) -> dict | None:
    """Finnhub news sentiment. A premium endpoint: returns None on free keys."""
    data = await _finnhub("/news-sentiment", {"symbol": ticker})
    if not isinstance(data, dict) or not data:
        return None
    return {
        "buzz": data.get("buzz", {}),
        "sentiment": data.get("sentiment", {}),
        "companyNewsScore": data.get("companyNewsScore"),
        "sectorAverageBullishPercent": data.get("sectorAverageBullishPercent"),
        "sectorAverageNewsScore": data.get("sectorAverageNewsScore"),
    }
