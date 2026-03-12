from fastapi import APIRouter, HTTPException
from app.services.fmp_service import (
    get_company_profile,
    get_financial_ratios,
    get_income_statement,
    get_competitor_ratios
)

router = APIRouter()

@router.get("/{ticker}/profile")
def company_profile(ticker: str):
    data = get_company_profile(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
    return data

@router.get("/{ticker}/ratios")
def financial_ratios(ticker: str):
    data = get_financial_ratios(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"No ratios found for {ticker}")
    return data

@router.get("/{ticker}/income")
def income_statement(ticker: str):
    data = get_income_statement(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"No income data found for {ticker}")
    return data

@router.get("/{ticker}/competitors")
def competitor_comparison(ticker: str):
    data = get_competitor_ratios(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"No competitor data found for {ticker}")
    return data
    