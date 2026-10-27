from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.deps import ticker_param
from app.rag import diff, qa, retriever, store
from app.rag.embeddings import get_embedder
from app.rag.ingest import index_ticker

router = APIRouter()


class Question(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


@router.get("/{ticker}/documents")
async def documents(ticker: str = Depends(ticker_param)):
    embedder = get_embedder()
    return {
        "ticker": ticker,
        "retrieval": "hybrid" if embedder else "bm25",
        "embedder": embedder.name if embedder else None,
        "documents": await run_in_threadpool(store.list_documents, ticker),
    }


@router.post("/{ticker}/index")
async def index(
    ticker: str = Depends(ticker_param),
    annual: int = Query(2, ge=0, le=5),
    quarterly: int = Query(3, ge=0, le=8),
    calls: int = Query(4, ge=0, le=8),
):
    """Fetch, chunk, embed and index recent 10-Ks, 10-Qs and earnings calls (idempotent)."""
    return await run_in_threadpool(index_ticker, ticker, annual, quarterly, calls)


@router.get("/{ticker}/search")
async def search(
    ticker: str = Depends(ticker_param), q: str = Query(..., min_length=2), k: int = Query(8, ge=1, le=25)
):
    hits = await run_in_threadpool(retriever.search, ticker, q, k)
    return {"ticker": ticker, "query": q, "hits": [h.to_dict() for h in hits]}


@router.post("/{ticker}/ask")
async def ask(body: Question, ticker: str = Depends(ticker_param)):
    """Answer a question from the filings with sentence-level citations."""
    return await qa.ask(ticker, body.question)


@router.get("/{ticker}/risk-diff")
async def risk_diff(ticker: str = Depends(ticker_param)):
    """What changed in Risk Factors between the last two 10-Ks."""
    return await diff.diff_risk_factors(ticker)
