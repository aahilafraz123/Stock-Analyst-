import yfinance as yf

def get_company_profile(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info
    if not info:
        return None
    return {
        "symbol": ticker,
        "companyName": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "description": info.get("longBusinessSummary"),
        "marketCap": info.get("marketCap"),
        "website": info.get("website"),
        "country": info.get("country"),
        "employees": info.get("fullTimeEmployees"),
        "currentPrice": info.get("currentPrice"),
    }

def get_financial_ratios(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info
    if not info:
        return None
    return {
        "peRatio": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "pbRatio": info.get("priceToBook"),
        "debtToEquity": info.get("debtToEquity"),
        "returnOnEquity": info.get("returnOnEquity"),
        "returnOnAssets": info.get("returnOnAssets"),
        "grossMargin": info.get("grossMargins"),
        "operatingMargin": info.get("operatingMargins"),
        "profitMargin": info.get("profitMargins"),
        "revenueGrowth": info.get("revenueGrowth"),
        "earningsGrowth": info.get("earningsGrowth"),
        "currentRatio": info.get("currentRatio"),
        "quickRatio": info.get("quickRatio"),
        "evToEbitda": info.get("enterpriseToEbitda"),
        "priceToSales": info.get("priceToSalesTrailing12Months"),
    }

def get_income_statement(ticker: str):
    stock = yf.Ticker(ticker)
    financials = stock.quarterly_financials
    if financials is None or financials.empty:
        return None
    return financials.to_dict()

def get_peers(ticker: str):
    peers_map = {
        "AAPL": ["MSFT", "GOOGL", "META", "AMZN", "NVDA"],
        "MSFT": ["AAPL", "GOOGL", "AMZN", "META", "NVDA"],
        "GOOGL": ["MSFT", "META", "AAPL", "AMZN", "SNAP"],
        "META": ["GOOGL", "SNAP", "PINS", "MSFT", "AMZN"],
        "AMZN": ["MSFT", "GOOGL", "AAPL", "WMT", "TGT"],
        "NVDA": ["AMD", "INTC", "QCOM", "AVGO", "TSM"],
        "TSLA": ["F", "GM", "RIVN", "NIO", "LCID"],
        "JPM": ["BAC", "WFC", "GS", "MS", "C"],
        "JNJ": ["PFE", "MRK", "ABBV", "LLY", "BMY"],
    }
    return peers_map.get(ticker.upper(), ["SPY"])

def get_competitor_ratios(ticker: str):
    peers = get_peers(ticker)
    all_tickers = [ticker] + peers[:5]
    results = {}
    for t in all_tickers:
        ratios = get_financial_ratios(t)
        profile = get_company_profile(t)
        if ratios and profile:
            results[t] = {
                "name": profile.get("companyName"),
                "sector": profile.get("sector"),
                "marketCap": profile.get("marketCap"),
                "peRatio": ratios.get("peRatio"),
                "pbRatio": ratios.get("pbRatio"),
                "debtToEquity": ratios.get("debtToEquity"),
                "returnOnEquity": ratios.get("returnOnEquity"),
                "grossMargin": ratios.get("grossMargin"),
                "evToEbitda": ratios.get("evToEbitda"),
            }
    return results

def get_price_context(ticker: str):
    """Get historical price context and momentum data"""
    stock = yf.Ticker(ticker)
    info = stock.info

    if not info:
        return None

    current_price = info.get("currentPrice")
    week52_high = info.get("fiftyTwoWeekHigh")
    week52_low = info.get("fiftyTwoWeekLow")

    price_position = None
    if week52_high and week52_low and current_price:
        range_size = week52_high - week52_low
        if range_size > 0:
            price_position = round(
                ((current_price - week52_low) / range_size) * 100, 1
            )

    hist = stock.history(period="3mo")
    price_1mo_ago = None
    price_3mo_ago = None
    change_1mo = None
    change_3mo = None

    if not hist.empty:
        price_3mo_ago = round(hist["Close"].iloc[0], 2)
        if len(hist) >= 21:
            price_1mo_ago = round(hist["Close"].iloc[-21], 2)

        if current_price and price_3mo_ago:
            change_3mo = round(
                ((current_price - price_3mo_ago) / price_3mo_ago) * 100, 1
            )
        if current_price and price_1mo_ago:
            change_1mo = round(
                ((current_price - price_1mo_ago) / price_1mo_ago) * 100, 1
            )

    return {
        "currentPrice": current_price,
        "52weekHigh": week52_high,
        "52weekLow": week52_low,
        "52weekRange": f"${week52_low} - ${week52_high}" if week52_low and week52_high else None,
        "priceVs52weekRange": f"{price_position}% of range" if price_position else None,
        "change1Month": f"{change_1mo}%" if change_1mo is not None else None,
        "change3Month": f"{change_3mo}%" if change_3mo is not None else None,
        "50dayAverage": info.get("fiftyDayAverage"),
        "200dayAverage": info.get("twoHundredDayAverage"),
        "priceVs50dma": round(
            ((current_price - info.get("fiftyDayAverage")) /
             info.get("fiftyDayAverage")) * 100, 1
        ) if current_price and info.get("fiftyDayAverage") else None,
        "priceVs200dma": round(
            ((current_price - info.get("twoHundredDayAverage")) /
             info.get("twoHundredDayAverage")) * 100, 1
        ) if current_price and info.get("twoHundredDayAverage") else None,
    }

def get_price_history(ticker: str):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo")
    if hist is None or hist.empty:
        return None
    result = []
    for date, row in hist.iterrows():
        result.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })
    return result

def get_analyst_consensus(ticker: str):
    """Get Wall Street analyst consensus and price targets"""
    stock = yf.Ticker(ticker)
    info = stock.info

    if not info:
        return None

    current_price = info.get("currentPrice")
    target_price = info.get("targetMeanPrice")

    upside = None
    if current_price and target_price:
        upside = round(((target_price - current_price) / current_price) * 100, 1)

    return {
        "targetHighPrice": info.get("targetHighPrice"),
        "targetLowPrice": info.get("targetLowPrice"),
        "targetMeanPrice": target_price,
        "targetMedianPrice": info.get("targetMedianPrice"),
        "impliedUpside": f"{upside}%" if upside is not None else None,
        "numberOfAnalysts": info.get("numberOfAnalystOpinions"),
        "recommendationMean": info.get("recommendationMean"),
        "recommendationKey": info.get("recommendationKey"),
    }