"""Peer companies: Finnhub's peer list when a key is configured, else a curated fallback."""

import logging
import re

import requests

from app.cache import DAY, cached
from app.config import settings
from app.net import DEFAULT_TIMEOUT

log = logging.getLogger(__name__)

_FALLBACK = {
    "AAPL": ["MSFT", "GOOGL", "META", "AMZN", "NVDA"],
    "MSFT": ["AAPL", "GOOGL", "AMZN", "META", "ORCL"],
    "GOOGL": ["MSFT", "META", "AAPL", "AMZN", "SNAP"],
    "GOOG": ["MSFT", "META", "AAPL", "AMZN", "SNAP"],
    "META": ["GOOGL", "SNAP", "PINS", "MSFT", "AMZN"],
    "AMZN": ["MSFT", "GOOGL", "AAPL", "WMT", "COST"],
    "NVDA": ["AMD", "INTC", "QCOM", "AVGO", "TSM"],
    "AMD": ["NVDA", "INTC", "QCOM", "AVGO", "ARM"],
    "TSLA": ["F", "GM", "RIVN", "TM", "LCID"],
    "JPM": ["BAC", "WFC", "GS", "MS", "C"],
    "JNJ": ["PFE", "MRK", "ABBV", "LLY", "BMY"],
    "NFLX": ["DIS", "WBD", "PARA", "ROKU", "SPOT"],
    "WMT": ["COST", "TGT", "AMZN", "KR", "DG"],
}

# Finnhub returns exchange-suffixed listings (e.g. "0700.HK"); keep plain US tickers.
_US_TICKER = re.compile(r"^[A-Z]{1,5}(-[A-Z])?$")


@cached("finnhub.peers", ttl=7 * DAY)
def _finnhub_peers(ticker: str) -> list[str] | None:
    response = requests.get(
        "https://finnhub.io/api/v1/stock/peers",
        params={"symbol": ticker, "token": settings.finnhub_api_key},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        return None
    peers = [p for p in data if isinstance(p, str) and p != ticker and _US_TICKER.match(p)]
    return peers or None


def get_peers(ticker: str) -> list[str]:
    ticker = ticker.upper()
    if settings.finnhub_api_key:
        try:
            if peers := _finnhub_peers(ticker):
                return peers[:5]
        except Exception as exc:
            log.info("Finnhub peers unavailable for %s: %s", ticker, exc)
    return _FALLBACK.get(ticker, [])
