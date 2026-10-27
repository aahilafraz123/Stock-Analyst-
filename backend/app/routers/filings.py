from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.deps import ticker_param
from app.services import edgar

router = APIRouter()

FORM = Query("10-Q", pattern="^(10-K|10-Q)$")


@router.get("/{ticker}")
async def recent_filings(ticker: str = Depends(ticker_param), form: str = FORM, limit: int = Query(4, ge=1, le=12)):
    return await run_in_threadpool(edgar.list_filings, ticker, form, limit)


@router.get("/{ticker}/text")
async def filing_text(ticker: str = Depends(ticker_param), form: str = FORM, index: int = Query(0, ge=0, le=8)):
    """Extracted sections (Business, Risk Factors, MD&A, Market Risk) of one filing."""
    return await run_in_threadpool(edgar.get_filing, ticker, form, index)
