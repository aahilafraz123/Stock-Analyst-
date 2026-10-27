from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from app.deps import ticker_param
from app.errors import NotFoundError
from app.services import history

router = APIRouter()


@router.get("/track-record")
async def track_record(min_age_days: float = Query(7, ge=0, le=365)):
    """Hit rate and excess return vs. SPY of every stored recommendation."""
    return await run_in_threadpool(history.track_record, min_age_days)


@router.get("")
async def all_reports(limit: int = Query(50, ge=1, le=200)):
    return await run_in_threadpool(history.list_reports, None, limit)


@router.get("/id/{report_id}")
async def report_by_id(report_id: int):
    report = await run_in_threadpool(history.get, report_id)
    if not report:
        raise NotFoundError(f"Report {report_id} not found")
    return report


@router.get("/{ticker}")
async def reports_for_ticker(ticker: str, limit: int = Query(20, ge=1, le=100)):
    return await run_in_threadpool(history.list_reports, ticker_param(ticker), limit)
