"""Insider (Form 4) transactions and the six-month net purchase summary, via yfinance."""

import logging

import yfinance as yf

from app.cache import HOUR, cached
from app.errors import NotFoundError
from app.services.market_data import num

log = logging.getLogger(__name__)


def classify_transaction(text: str) -> str:
    text = text.lower()
    if any(w in text for w in ("sale", "sold", "sell")):
        return "SELL"
    if any(w in text for w in ("purchase", "bought", "buy")):
        return "BUY"
    if "gift" in text:
        return "GIFT"
    if any(w in text for w in ("award", "grant")):
        return "AWARD"
    if "exercise" in text or "conversion" in text:
        return "EXERCISE"
    return "OTHER"


@cached("yf.insider", ttl=6 * HOUR)
def get_insider_trades(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    transactions = stock.insider_transactions
    if transactions is None or transactions.empty:
        raise NotFoundError(f"No insider transactions for {ticker}")

    trades = []
    for _, row in transactions.head(15).iterrows():
        text = str(row.get("Text") or "")
        trades.append(
            {
                "insider": str(row.get("Insider") or "Unknown"),
                "position": str(row.get("Position") or ""),
                "action": classify_transaction(text),
                "shares": int(num(row.get("Shares")) or 0),
                "value": num(row.get("Value")),
                "date": str(row.get("Start Date") or "")[:10],
                "description": text[:120],
                "ownership": str(row.get("Ownership") or ""),
            }
        )

    summary_lines = []
    purchases = stock.insider_purchases
    if purchases is not None and not purchases.empty:
        label_col = purchases.columns[0]  # "Insider Purchases Last 6m"
        for _, row in purchases.iterrows():
            label = str(row.get(label_col, ""))
            shares = num(row.get("Shares")) or 0
            trans = num(row.get("Trans")) or 0
            if label == "Purchases":
                summary_lines.append(f"Purchases last 6 months: {int(shares):,} shares in {int(trans)} transactions.")
            elif label == "Sales":
                summary_lines.append(f"Sales last 6 months: {int(shares):,} shares in {int(trans)} transactions.")
            elif label.startswith("Net Shares"):
                direction = "net bought" if shares > 0 else "net sold"
                summary_lines.append(f"Insiders {direction} {abs(int(shares)):,} shares over the last 6 months.")

    return {
        "ticker": ticker.upper(),
        "trades": trades,
        "summary": " ".join(summary_lines) or None,
        "buyCount": sum(t["action"] == "BUY" for t in trades),
        "sellCount": sum(t["action"] == "SELL" for t in trades),
    }
