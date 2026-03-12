from fastapi import APIRouter, HTTPException
from app.services.news_service import (
    get_company_news,
    get_market_news,
    get_company_sentiment
)

router = APIRouter()

@router.get("/{ticker}")
async def company_news(ticker: str, days_back: int = 7):
    data = await get_company_news(ticker.upper(), days_back)
    if not data:
        raise HTTPException(status_code=404, detail=f"No news found for {ticker}")
    return data

@router.get("/{ticker}/sentiment")
async def company_sentiment(ticker: str):
    data = await get_company_sentiment(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"No sentiment data found for {ticker}")
    return data

@router.get("/market/{category}")
async def market_news(category: str = "general"):
    valid = ["general", "forex", "crypto", "merger"]
    if category not in valid:
        raise HTTPException(status_code=400, detail=f"Category must be one of {valid}")
    data = await get_market_news(category)
    if not data:
        raise HTTPException(status_code=404, detail="No market news found")
    return data
    