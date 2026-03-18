import yfinance as yf

def get_institutional_ownership(ticker: str) -> dict:
    """
    Fetch institutional ownership data using yFinance.
    """
    try:
        stock = yf.Ticker(ticker)

        major_holders = stock.major_holders
        institutional_holders = stock.institutional_holders
        mutualfund_holders = stock.mutualfund_holders

        result = {"ticker": ticker.upper()}

        # Major holders summary
        if major_holders is not None and not major_holders.empty:
            holders_dict = {}
            for _, row in major_holders.iterrows():
                label = str(row.get("Breakdown", ""))
                value = row.get("Value", "")
                holders_dict[label] = value
            result["majorHoldersSummary"] = holders_dict

        # Top institutional holders
        if institutional_holders is not None and not institutional_holders.empty:
            inst_list = []
            for _, row in institutional_holders.head(10).iterrows():
                pct_change = row.get("pctChange", 0)
                inst_list.append({
                    "holder": str(row.get("Holder", "")),
                    "shares": int(row.get("Shares", 0)),
                    "value": float(row.get("Value", 0)),
                    "pctHeld": float(row.get("pctHeld", 0)),
                    "pctChange": float(pct_change) if pct_change else 0,
                    "dateReported": str(row.get("Date Reported", ""))[:10],
                    "increasing": float(pct_change) > 0 if pct_change else None,
                })
            result["topInstitutions"] = inst_list

        # Top mutual fund holders
        if mutualfund_holders is not None and not mutualfund_holders.empty:
            fund_list = []
            for _, row in mutualfund_holders.head(5).iterrows():
                fund_list.append({
                    "holder": str(row.get("Holder", "")),
                    "shares": int(row.get("Shares", 0)),
                    "value": float(row.get("Value", 0)),
                    "pctHeld": float(row.get("pctHeld", 0)),
                    "pctChange": float(row.get("pctChange", 0)),
                    "dateReported": str(row.get("Date Reported", ""))[:10],
                })
            result["topMutualFunds"] = fund_list

        # Build summary
        summary_parts = []
        mhs = result.get("majorHoldersSummary", {})

        insider_pct = mhs.get("insidersPercentHeld")
        inst_pct = mhs.get("institutionsPercentHeld")
        inst_count = mhs.get("institutionsCount")

        if inst_pct:
            summary_parts.append(f"{float(inst_pct)*100:.1f}% held by institutions.")
        if insider_pct:
            summary_parts.append(f"{float(insider_pct)*100:.2f}% held by insiders.")
        if inst_count:
            summary_parts.append(f"{int(inst_count):,} institutional holders total.")

        # Note which major institutions are increasing vs decreasing
        if result.get("topInstitutions"):
            top = result["topInstitutions"][0]
            summary_parts.append(
                f"Largest holder: {top['holder']} with {top['pctHeld']*100:.2f}% of shares."
            )
            increasing = [i["holder"] for i in result["topInstitutions"] if i.get("increasing")]
            decreasing = [i["holder"] for i in result["topInstitutions"] if i.get("increasing") == False]
            if increasing:
                summary_parts.append(f"Recently increasing positions: {', '.join(increasing[:3])}.")
            if decreasing:
                summary_parts.append(f"Recently decreasing positions: {', '.join(decreasing[:3])}.")

        result["summary"] = " ".join(summary_parts)
        return result

    except Exception as e:
        print(f"[{ticker}] Institutional ownership fetch failed: {e}")
        return None