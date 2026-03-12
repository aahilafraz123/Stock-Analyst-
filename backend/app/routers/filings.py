from fastapi import APIRouter, HTTPException
from app.services.edgar_service import get_recent_10q_filings, get_10q_text

router = APIRouter()

@router.get("/{ticker}")
def recent_filings(ticker: str):
    data = get_recent_10q_filings(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"No filings found for {ticker}")
    return data

@router.get("/{ticker}/text")
def filing_text(ticker: str):
    data = get_10q_text(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"Could not retrieve 10-Q for {ticker}")
    return data