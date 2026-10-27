from fastapi import APIRouter, Depends, Query

from app.deps import ticker_param
from app.errors import InvalidInputError, NotFoundError
from app.services import news

router = APIRouter()

MARKET_CATEGORIES = ("general", "forex", "crypto", "merger")


@router.get("/market/{category}")
async def market_news(category: str = "general"):
    if category not in MARKET_CATEGORIES:
        raise InvalidInputError(f"Category must be one of {list(MARKET_CATEGORIES)}")
    return await news.get_market_news(category)


@router.get("/{ticker}")
async def company_news(ticker: str = Depends(ticker_param), days_back: int = Query(7, ge=1, le=30)):
    return await news.get_company_news(ticker, days_back=days_back, limit=10, with_bodies=False)


@router.get("/{ticker}/sentiment")
async def company_sentiment(ticker: str = Depends(ticker_param)):
    data = await news.get_company_sentiment(ticker)
    if not data:
        raise NotFoundError(f"No sentiment data for {ticker} (Finnhub premium endpoint)")
    return data
