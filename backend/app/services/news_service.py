import httpx
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
BASE_URL = "https://finnhub.io/api/v1"

async def fetch_article_text(url: str) -> str:
    """Fetch and extract clean text from a news article URL"""
    if not url:
        return ""
    try:
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        # Return first 2000 chars of body — enough context without blowing up the prompt
        return article.text[:2000] if article.text else ""
    except Exception:
        return ""

async def get_company_news(ticker: str, days_back: int = 7):
    """Get recent news articles with full body text for a specific ticker"""
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/company-news"
    params = {
        "symbol": ticker,
        "from": start_date,
        "to": end_date,
        "token": FINNHUB_API_KEY
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        data = response.json()

    if not data:
        return []

    # Limit to 5 most recent articles and fetch their full text
    # We cap at 5 because fetching full articles takes time
    articles = []
    for item in data[:5]:
        article_url = item.get("url", "")
        body = await fetch_article_text(article_url)

        articles.append({
            "headline": item.get("headline"),
            "summary": item.get("summary"),
            "body": body,
            "source": item.get("source"),
            "url": article_url,
            "datetime": datetime.fromtimestamp(
                item.get("datetime", 0)
            ).strftime("%Y-%m-%d %H:%M"),
        })

    return articles

async def get_market_news(category: str = "general"):
    """Get broad market news"""
    url = f"{BASE_URL}/news"
    params = {
        "category": category,
        "token": FINNHUB_API_KEY
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        data = response.json()

    if not data:
        return []

    articles = []
    for item in data[:20]:
        articles.append({
            "headline": item.get("headline"),
            "summary": item.get("summary"),
            "source": item.get("source"),
            "url": item.get("url"),
            "datetime": datetime.fromtimestamp(
                item.get("datetime", 0)
            ).strftime("%Y-%m-%d %H:%M"),
        })

    return articles

async def get_company_sentiment(ticker: str):
    """Get news sentiment score for a ticker"""
    url = f"{BASE_URL}/news-sentiment"
    params = {
        "symbol": ticker,
        "token": FINNHUB_API_KEY
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        data = response.json()

    if not data:
        return None

    return {
        "buzz": data.get("buzz", {}),
        "sentiment": data.get("sentiment", {}),
        "companyNewsScore": data.get("companyNewsScore"),
        "sectorAverageBullishPercent": data.get("sectorAverageBullishPercent"),
        "sectorAverageNewsScore": data.get("sectorAverageNewsScore"),
    }