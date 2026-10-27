from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.deps import ticker_param
from app.errors import NotFoundError
from app.services import market_data

router = APIRouter()


@router.get("/{ticker}/profile")
async def company_profile(ticker: str = Depends(ticker_param)):
    return await run_in_threadpool(market_data.get_company_profile, ticker)


@router.get("/{ticker}/ratios")
async def financial_ratios(ticker: str = Depends(ticker_param)):
    return await run_in_threadpool(market_data.get_financial_ratios, ticker)


@router.get("/{ticker}/income")
async def income_statement(ticker: str = Depends(ticker_param)):
    data = await run_in_threadpool(market_data.get_income_statement, ticker)
    if not data:
        raise NotFoundError(f"No income statement data for {ticker}")
    return data


@router.get("/{ticker}/competitors")
async def competitor_comparison(ticker: str = Depends(ticker_param)):
    return await run_in_threadpool(market_data.get_competitor_ratios, ticker)


@router.get("/{ticker}/history")
async def price_history(
    ticker: str = Depends(ticker_param),
    period: str = Query("1Y", pattern="^(1W|1M|3M|6M|1Y|2Y|5Y)$"),
):
    return await run_in_threadpool(market_data.get_price_history, ticker, period)


@router.get("/{ticker}/snapshot")
async def snapshot(ticker: str = Depends(ticker_param)):
    """Profile + ratios + analyst consensus in one round trip (they share one upstream fetch)."""

    def build():
        return {
            "profile": market_data.get_company_profile(ticker),
            "ratios": market_data.get_financial_ratios(ticker),
            "analysts": market_data.get_analyst_consensus(ticker),
            "price": market_data.get_price_context(ticker),
        }

    return await run_in_threadpool(build)
