from fastapi import APIRouter, HTTPException
from app.services.ai_service import analyze_stock
import traceback

router = APIRouter()

@router.get("/{ticker}")
async def stock_analysis(ticker: str):
    try:
        result = await analyze_stock(ticker.upper())
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))