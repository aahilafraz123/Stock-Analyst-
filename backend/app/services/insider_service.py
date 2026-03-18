import yfinance as yf
import pandas as pd

def get_insider_trades(ticker: str) -> dict:
    """
    Fetch insider trading data using yFinance.
    Returns recent transactions and a 6-month summary.
    """
    try:
        stock = yf.Ticker(ticker)

        # Get recent transactions
        transactions = stock.insider_transactions
        purchases = stock.insider_purchases

        if transactions is None or transactions.empty:
            return None

        # Clean up transactions dataframe
        transactions = transactions.copy()
        transactions = transactions.fillna(0)

        # Build list of recent trades
        trades = []
        for _, row in transactions.head(10).iterrows():
            text = str(row.get("Text", ""))
            shares = row.get("Shares", 0)
            value = row.get("Value", 0)
            insider = row.get("Insider", "Unknown")
            position = row.get("Position", "Unknown")
            start_date = str(row.get("Start Date", ""))[:10]
            ownership = row.get("Ownership", "")

            # Determine if buy or sell from text
            text_lower = text.lower()
            if any(word in text_lower for word in ["sale", "sold", "sell"]):
                action = "SELL"
            elif any(word in text_lower for word in ["purchase", "bought", "buy"]):
                action = "BUY"
            elif "gift" in text_lower:
                action = "GIFT"
            else:
                action = "OTHER"

            trades.append({
                "insider": insider,
                "position": position,
                "action": action,
                "shares": int(shares) if shares else 0,
                "value": float(value) if value else 0,
                "date": start_date,
                "description": text[:100] if text else "",
                "ownership": ownership,
            })

        # Build summary from purchases dataframe
        summary_lines = []
        if purchases is not None and not purchases.empty:
            for _, row in purchases.iterrows():
                label = str(row.get("Insider Purchases Last 6m", ""))
                shares = row.get("Shares", 0)
                trans = row.get("Trans", 0)

                if label == "Purchases":
                    summary_lines.append(f"Purchases last 6 months: {int(shares):,} shares across {int(trans)} transactions.")
                elif label == "Sales":
                    summary_lines.append(f"Sales last 6 months: {int(shares):,} shares across {int(trans)} transactions.")
                elif label == "Net Shares Purchased (Sold)":
                    net = int(shares)
                    direction = "net bought" if net > 0 else "net sold"
                    summary_lines.append(f"Insiders {direction} {abs(net):,} shares net over last 6 months.")
                elif label == "% Buy Shares":
                    pct = float(shares) * 100 if shares else 0
                    summary_lines.append(f"Buy ratio: {pct:.2f}% of insider activity.")

        summary = " ".join(summary_lines) if summary_lines else "Insider trading data available."

        # Count buys and sells
        buys = [t for t in trades if t["action"] == "BUY"]
        sells = [t for t in trades if t["action"] == "SELL"]

        return {
            "ticker": ticker.upper(),
            "trades": trades,
            "summary": summary,
            "buyCount": len(buys),
            "sellCount": len(sells),
        }

    except Exception as e:
        print(f"[{ticker}] Insider trade fetch failed: {e}")
        return None