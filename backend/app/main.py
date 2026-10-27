import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.errors import AppError, as_app_error
from app.rag.embeddings import get_embedder
from app.routers import analysis, filings, news, rag, reports, stocks

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("app")

app = FastAPI(
    title="StockAnalyzer API",
    version="2.0.0",
    description="Equity research pipeline: market data, SEC filings, earnings calls and news, "
    "retrieved with hybrid search and synthesised by Claude into cited reports.",
)


@app.middleware("http")
async def errors_and_timing(request: Request, call_next):
    """Turn exceptions into JSON *inside* the CORS middleware, so browsers see the real
    error instead of a misleading CORS failure, and log request timings."""
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        err = as_app_error(exc)
        if type(err) is AppError:
            log.exception("Unhandled error on %s", request.url.path)
        else:
            log.warning("%s on %s: %s", err.code, request.url.path, err.message)
        response = JSONResponse(err.to_dict(), status_code=err.status_code)
    log.info(
        "%s %s -> %s (%dms)",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(exc.to_dict(), status_code=exc.status_code)


# Added last = outermost, so even error responses carry CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/stocks", tags=["market data"])
app.include_router(news.router, prefix="/news", tags=["news"])
app.include_router(filings.router, prefix="/filings", tags=["sec filings"])
app.include_router(analysis.router, prefix="/analysis", tags=["ai analysis"])
app.include_router(rag.router, prefix="/rag", tags=["retrieval"])
app.include_router(reports.router, prefix="/reports", tags=["report history"])


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "StockAnalyzer API", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health():
    embedder = get_embedder()
    return {
        "status": "ok",
        "model": settings.anthropic_model,
        "configured": {
            "anthropic": bool(settings.anthropic_api_key),
            "finnhub": bool(settings.finnhub_api_key),
            "earningscall": bool(settings.earningscall_api_key),
            "voyage": bool(settings.voyage_api_key),
        },
        "retrieval": "hybrid" if embedder else "bm25",
        "embedder": embedder.name if embedder else None,
    }
