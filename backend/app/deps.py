"""Shared request dependencies."""

import re

from fastapi import Path

from app.errors import InvalidInputError

_TICKER = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def ticker_param(ticker: str = Path(..., description="Stock ticker, e.g. AAPL or BRK.B")) -> str:
    ticker = ticker.strip().upper()
    if not _TICKER.match(ticker):
        raise InvalidInputError(f"'{ticker}' is not a valid ticker symbol")
    return ticker
