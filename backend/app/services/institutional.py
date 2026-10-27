"""Institutional and mutual fund ownership (13F-derived), via yfinance."""

import logging

import yfinance as yf

from app.cache import HOUR, cached
from app.errors import NotFoundError
from app.services.market_data import num

log = logging.getLogger(__name__)


def major_holders_summary(major_holders) -> dict:
    """yfinance puts the labels (insidersPercentHeld, ...) in the index, not a column."""
    if major_holders is None or major_holders.empty:
        return {}
    column = "Value" if "Value" in major_holders.columns else major_holders.columns[0]
    return {str(label): num(value) for label, value in major_holders[column].items()}


def _holders(df, limit: int) -> list[dict]:
    if df is None or df.empty:
        return []
    rows = []
    for _, row in df.head(limit).iterrows():
        pct_change = num(row.get("pctChange"))
        rows.append(
            {
                "holder": str(row.get("Holder", "")),
                "shares": int(num(row.get("Shares")) or 0),
                "value": num(row.get("Value")),
                "pctHeld": num(row.get("pctHeld")),
                "pctChange": pct_change,
                "dateReported": str(row.get("Date Reported", ""))[:10],
                "increasing": None if not pct_change else pct_change > 0,
            }
        )
    return rows


@cached("yf.institutional", ttl=12 * HOUR)
def get_institutional_ownership(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    major = major_holders_summary(stock.major_holders)
    institutions = _holders(stock.institutional_holders, 10)
    funds = _holders(stock.mutualfund_holders, 5)
    if not major and not institutions:
        raise NotFoundError(f"No ownership data for {ticker}")

    parts = []
    if (pct := major.get("institutionsPercentHeld")) is not None:
        parts.append(f"{pct * 100:.1f}% held by institutions.")
    if (pct := major.get("insidersPercentHeld")) is not None:
        parts.append(f"{pct * 100:.2f}% held by insiders.")
    if (count := major.get("institutionsCount")) is not None:
        parts.append(f"{int(count):,} institutional holders.")
    if institutions:
        top = institutions[0]
        if top["pctHeld"] is not None:
            parts.append(f"Largest holder: {top['holder']} ({top['pctHeld'] * 100:.2f}%).")
        up = [i["holder"] for i in institutions if i["increasing"]]
        down = [i["holder"] for i in institutions if i["increasing"] is False]
        if up:
            parts.append(f"Increasing positions: {', '.join(up[:3])}.")
        if down:
            parts.append(f"Decreasing positions: {', '.join(down[:3])}.")

    return {
        "ticker": ticker.upper(),
        "majorHoldersSummary": major,
        "topInstitutions": institutions,
        "topMutualFunds": funds,
        "summary": " ".join(parts) or None,
    }
