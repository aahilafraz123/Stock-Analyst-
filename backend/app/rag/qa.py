"""'Ask the filings': retrieve passages, then answer with Claude's Citations API.

Retrieved chunks are passed as `document` blocks with citations enabled, so every
sentence in the answer carries the exact passage it came from, which the UI links
back to the SEC filing.
"""

import asyncio
import logging

from app import llm
from app.rag import retriever, store
from app.rag.ingest import index_ticker
from app.rag.store import SECTION_TITLES

log = logging.getLogger(__name__)

QA_SYSTEM = """You answer questions about a public company using only the provided excerpts from its SEC
filings and earnings calls. Be precise and concise (under 250 words), cite figures, and say clearly when the
excerpts do not contain the answer. Do not use outside knowledge."""


async def ensure_indexed(ticker: str) -> list[dict]:
    docs = store.list_documents(ticker)
    if not docs:
        await asyncio.to_thread(index_ticker, ticker, 1, 2, 2)
        docs = store.list_documents(ticker)
    return docs


def _documents(hits: list[retriever.Hit]) -> list[dict]:
    docs = []
    for h in hits:
        doc = {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": h.text},
            "title": f"{h.title} · {SECTION_TITLES.get(h.section, h.section)}",
            "citations": {"enabled": True},
        }
        if h.filed:
            doc["context"] = f"Filed/held {h.filed}"
        docs.append(doc)
    return docs


def _segments(blocks: list, hits: list[retriever.Hit]) -> list[dict]:
    segments = []
    for block in blocks:
        cites = []
        for c in getattr(block, "citations", None) or []:
            idx = getattr(c, "document_index", None)
            if idx is None or idx >= len(hits):
                continue
            cites.append({"source": idx, "citedText": getattr(c, "cited_text", "")})
        segments.append({"text": block.text, "citations": cites})
    return segments


async def ask(ticker: str, question: str, k: int = 8) -> dict:
    ticker = ticker.upper()
    docs = await ensure_indexed(ticker)
    hits = await asyncio.to_thread(retriever.search, ticker, question, k)
    if not hits:
        return {
            "ticker": ticker,
            "question": question,
            "answer": [{"text": "No relevant passages were found in the indexed filings.", "citations": []}],
            "sources": [],
            "documents": len(docs),
            "meta": None,
        }
    blocks, usage = await llm.cited_answer(QA_SYSTEM, _documents(hits), question)
    return {
        "ticker": ticker,
        "question": question,
        "answer": _segments(blocks, hits),
        "sources": [
            {
                "index": i,
                "chunkId": h.chunk_id,
                "label": f"{h.title} · {SECTION_TITLES.get(h.section, h.section)}",
                "url": h.url,
                "date": h.filed,
                "score": h.score,
                "excerpt": h.text[:500],
            }
            for i, h in enumerate(hits)
        ],
        "documents": len(docs),
        "meta": usage,
    }
