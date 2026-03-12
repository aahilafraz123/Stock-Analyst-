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
    