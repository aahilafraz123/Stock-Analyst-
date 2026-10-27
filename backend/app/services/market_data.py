"""Quotes, fundamentals, analyst targets and price history from Yahoo Finance (yfinance).

All public functions build on a single cached `get_info` call, so the profile,
ratios, price context and analyst consensus for a ticker cost one request.
"""

import logging
import math
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

from app.cache import HOUR, MINUTE, cached
from app.errors import NotFoundError, UpstreamError
from app.services.peers import get_peers

log = logging.getLogger(__name__)

SOURCE = "Yahoo Finance"


def num(value, digits: int | None = None):
    """Convert numpy/pandas scalars to plain floats, mapping NaN/inf to None."""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return round(value, digits) if digits is not None else value


def pct_change(new, old, digits: int = 1):
    if new is None or not old:
        return None
    return round((new - old) / old * 100, digits)


@cached("yf.info", ttl=15 * MINUTE)
def get_info(ticker: str) -> dict:
    try:
        info = yf.Ticker(ticker).info
    except Exception as exc:  # yfinance raises a zoo of exception types
        raise UpstreamError(f"Yahoo Finance request failed for {ticker}: {exc}", source=SOURCE) from exc
    price = (info or {}).get("currentPrice") or (info or {}).get("regularMarketPrice")
    if not info or (price is None and not info.get("longName") and not info.get("shortName")):
        raise NotFoundError(f"Ticker {ticker} not found", source=SOURCE)
    return info


def current_price(info: dict):
    return num(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"))


def get_company_profile(ticker: str) -> dict:
    info = get_info(ticker)
    return {
        "symbol": ticker,
        "companyName": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "description": info.get("longBusinessSummary"),
        "marketCap": num(info.get("marketCap")),
        "website": info.get("website"),
        "country": info.get("country"),
        "employees": info.get("fullTimeEmployees"),
        "currentPrice": current_price(info),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
    }


def get_financial_ratios(ticker: str) -> dict:
    info = get_info(ticker)
    fields = {
        "peRatio": "trailingPE",
        "forwardPE": "forwardPE",
        "pegRatio": "trailingPegRatio",
        "pbRatio": "priceToBook",
        "debtToEquity": "debtToEquity",
        "returnOnEquity": "returnOnEquity",
        "returnOnAssets": "returnOnAssets",
        "grossMargin": "grossMargins",
        "operatingMargin": "operatingMargins",
        "profitMargin": "profitMargins",
        "revenueGrowth": "revenueGrowth",
        "earningsGrowth": "earningsGrowth",
        "currentRatio": "currentRatio",
        "quickRatio": "quickRatio",
        "evToEbitda": "enterpriseToEbitda",
        "priceToSales": "priceToSalesTrailing12Months",
        "dividendYield": "dividendYield",
        "freeCashflow": "freeCashflow",
        "beta": "beta",
    }
    return {out: num(info.get(src)) for out, src in fields.items()}


@cached("yf.income", ttl=12 * HOUR)
def get_income_statement(ticker: str) -> dict | None:
    financials = yf.Ticker(ticker).quarterly_financials
    if financials is None or financials.empty:
        return None
    return {str(col.date()): {str(row): num(val) for row, val in financials[col].items()} for col in financials.columns}


def _peer_row(ticker: str) -> tuple[str, dict | None]:
    try:
        info = get_info(ticker)
    except Exception as exc:
        log.info("Skipping peer %s: %s", ticker, exc)
        return ticker, None
    return ticker, {
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "marketCap": num(info.get("marketCap")),
        "peRatio": num(info.get("trailingPE")),
        "forwardPE": num(info.get("forwardPE")),
        "pbRatio": num(info.get("priceToBook")),
        "debtToEquity": num(info.get("debtToEquity")),
        "returnOnEquity": num(info.get("returnOnEquity")),
        "grossMargin": num(info.get("grossMargins")),
        "operatingMargin": num(info.get("operatingMargins")),
        "revenueGrowth": num(info.get("revenueGrowth")),
        "evToEbitda": num(info.get("enterpriseToEbitda")),
    }


def get_competitor_ratios(ticker: str) -> dict:
    """The ticker plus up to five peers, fetched concurrently."""
    get_info(ticker)  # surface NotFound/Upstream errors for the main ticker
    tickers = [ticker, *get_peers(ticker)[:5]]
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = dict(pool.map(_peer_row, tickers))
    return {t: row for t, row in rows.items() if row}


_HISTORY_PERIODS = {
    "1W": ("7d", "30m"),
    "1M": ("1mo", "1d"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"),
    "2Y": ("2y", "1wk"),
    "5Y": ("5y", "1wk"),
}


@cached("yf.history", ttl=10 * MINUTE)
def get_price_history(ticker: str, period: str = "1Y") -> list[dict]:
    yf_period, interval = _HISTORY_PERIODS.get(period.upper(), ("1y", "1d"))
    try:
        hist = yf.Ticker(ticker).history(period=yf_period, interval=interval)
    except Exception as exc:
        raise UpstreamError(f"Price history unavailable for {ticker}: {exc}", source=SOURCE) from exc
    if hist is None or hist.empty:
        raise NotFoundError(f"No price history for {ticker}", source=SOURCE)
    fmt = "%Y-%m-%d" if interval in ("1d", "1wk") else "%Y-%m-%d %H:%M"
    return [
        {
            "date": dt.strftime(fmt),
            "open": num(row["Open"], 2),
            "high": num(row["High"], 2),
            "low": num(row["Low"], 2),
            "close": num(row["Close"], 2),
            "volume": int(row["Volume"]) if num(row["Volume"]) is not None else None,
        }
        for dt, row in hist.iterrows()
    ]


def get_price_context(ticker: str) -> dict:
    info = get_info(ticker)
    price = current_price(info)
    high, low = num(info.get("fiftyTwoWeekHigh")), num(info.get("fiftyTwoWeekLow"))
    sma50, sma200 = num(info.get("fiftyDayAverage")), num(info.get("twoHundredDayAverage"))

    position = None
    if price is not None and high and low and high > low:
        position = round((price - low) / (high - low) * 100, 1)

    closes = []
    try:
        closes = [p["close"] for p in get_price_history(ticker, "6M") if p["close"] is not None]
    except Exception as exc:
        log.info("No 6M history for %s: %s", ticker, exc)

    def change_over(days: int):
        return pct_change(price, closes[-days - 1], 1) if len(closes) > days else None

    return {
        "currentPrice": price,
        "52weekHigh": high,
        "52weekLow": low,
        "positionIn52weekRangePct": position,
        "change1MonthPct": change_over(21),
        "change3MonthPct": change_over(63),
        "change6MonthPct": pct_change(price, closes[0]) if closes else None,
        "50dayAverage": sma50,
        "200dayAverage": sma200,
        "priceVs50dmaPct": pct_change(price, sma50),
        "priceVs200dmaPct": pct_change(price, sma200),
    }


def get_analyst_consensus(ticker: str) -> dict:
    info = get_info(ticker)
    price = current_price(info)
    target = num(info.get("targetMeanPrice"))
    return {
        "targetHighPrice": num(info.get("targetHighPrice")),
        "targetLowPrice": num(info.get("targetLowPrice")),
        "targetMeanPrice": target,
        "targetMedianPrice": num(info.get("targetMedianPrice")),
        "impliedUpsidePct": pct_change(target, price),
        "numberOfAnalysts": info.get("numberOfAnalystOpinions"),
        "recommendationMean": num(info.get("recommendationMean")),
        "recommendationKey": info.get("recommendationKey"),
    }
