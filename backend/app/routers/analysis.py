import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.deps import ticker_param
from app.services.research import run_analysis, stream_analysis

router = APIRouter()


@router.get("/{ticker}")
async def stock_analysis(ticker: str = Depends(ticker_param), refresh: bool = Query(False)):
    """Run the full pipeline and return the finished report (recent reports are served from history)."""
    return await run_analysis(ticker, refresh=refresh)


@router.get("/{ticker}/stream")
async def stock_analysis_stream(ticker: str = Depends(ticker_param), refresh: bool = Query(False)):
    """Server-Sent Events: `source` and `stage` progress events, then a `report` or `error` event."""

    async def events():
        yield ": stream open\n\n"
        async for event in stream_analysis(ticker, refresh=refresh):
            yield f"event: {event['type']}\ndata: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
