"""Turn SEC filings and earnings call transcripts into indexed, embedded chunks."""

import logging

from app.rag import store
from app.rag.chunking import chunk_text
from app.rag.embeddings import get_embedder
from app.rag.store import SECTION_TITLES, DocumentMeta, contextual_body
from app.services import edgar, transcripts

log = logging.getLogger(__name__)


def filing_doc_id(filing: dict) -> str:
    return f"{filing['ticker']}:{filing['accessionNumber']}"


def transcript_doc_id(t: dict) -> str:
    return f"{t['ticker']}:call-{t['year']}Q{t['quarter']}"


def _filing_title(filing: dict) -> str:
    period = filing.get("reportDate") or filing.get("filingDate")
    label = "fiscal year ended" if filing["form"] == "10-K" else "quarter ended"
    return f"{filing['ticker']} {filing['form']} ({label} {period})"


def _store(meta: DocumentMeta, sections: dict[str, str]) -> int:
    chunks = [c for name, text in sections.items() if text for c in chunk_text(text, name)]
    embedder = get_embedder()
    vectors = None
    if embedder and chunks:
        try:
            bodies = [contextual_body(meta.title, SECTION_TITLES.get(c.section, c.section), c.text) for c in chunks]
            vectors = embedder.embed(bodies, kind="document")
        except Exception as exc:
            log.warning("Embedding %s failed; indexing for BM25 only: %s", meta.doc_id, exc)
    store.add_document(meta, chunks, vectors, embedder.name if embedder else None)
    log.info("Indexed %s: %d chunks (%s)", meta.doc_id, len(chunks), "hybrid" if vectors is not None else "bm25")
    return len(chunks)


def ingest_filing(filing: dict) -> str:
    doc_id = filing_doc_id(filing)
    if not store.has_document(doc_id):
        meta = DocumentMeta(
            doc_id=doc_id,
            ticker=filing["ticker"],
            kind="filing",
            form=filing["form"],
            title=_filing_title(filing),
            period=filing.get("reportDate"),
            filed=filing.get("filingDate"),
            url=filing.get("url"),
        )
        _store(meta, filing["sections"])
    return doc_id


def ingest_transcript(t: dict) -> str:
    doc_id = transcript_doc_id(t)
    if not store.has_document(doc_id):
        meta = DocumentMeta(
            doc_id=doc_id,
            ticker=t["ticker"],
            kind="transcript",
            form="EARNINGS_CALL",
            title=f"{t['ticker']} Q{t['quarter']} {t['year']} earnings call",
            period=f"{t['year']}Q{t['quarter']}",
            filed=t.get("conferenceDate"),
        )
        _store(meta, {"prepared_remarks": t.get("preparedRemarks", ""), "qa": t.get("qaSection", "")})
    return doc_id


def index_ticker(ticker: str, n_10k: int = 2, n_10q: int = 3, n_transcripts: int = 4) -> dict:
    """Index a ticker's recent filings and calls. Already-indexed documents are skipped."""
    ticker = ticker.upper()
    results: list[dict] = []
    for form, count in (("10-K", n_10k), ("10-Q", n_10q)):
        for i in range(count):
            try:
                filing = edgar.get_filing(ticker, form, index=i)
                results.append({"docId": ingest_filing(filing), "status": "ok"})
            except Exception as exc:
                results.append({"docId": f"{ticker}:{form}#{i}", "status": "error", "detail": str(exc)})
                break
    try:
        for t in transcripts.get_transcripts(ticker, limit=n_transcripts):
            results.append({"docId": ingest_transcript(t), "status": "ok"})
    except Exception as exc:
        results.append({"docId": f"{ticker}:calls", "status": "error", "detail": str(exc)})
    return {"ticker": ticker, "results": results, "documents": store.list_documents(ticker)}
