"""SQLite-backed document store: chunk text, FTS5 (BM25) index and dense vectors.

One file, no vector database to run. At this scale (a few thousand chunks per
ticker) brute-force cosine similarity in numpy takes well under 10 ms.
"""

import re
import sqlite3
import time
from dataclasses import dataclass

import numpy as np

from app import db
from app.rag.chunking import Chunk

db.register_schema(
    """
    CREATE TABLE IF NOT EXISTS rag_documents (
        doc_id      TEXT PRIMARY KEY,
        ticker      TEXT NOT NULL,
        kind        TEXT NOT NULL,          -- filing | transcript
        form        TEXT,                   -- 10-K, 10-Q, EARNINGS_CALL
        title       TEXT NOT NULL,
        period      TEXT,
        filed       TEXT,
        url         TEXT,
        chunk_count INTEGER NOT NULL DEFAULT 0,
        embed_model TEXT,
        ingested_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS rag_documents_ticker ON rag_documents(ticker);

    CREATE TABLE IF NOT EXISTS rag_chunks (
        chunk_id  TEXT PRIMARY KEY,
        doc_id    TEXT NOT NULL REFERENCES rag_documents(doc_id) ON DELETE CASCADE,
        ticker    TEXT NOT NULL,
        section   TEXT NOT NULL,
        ordinal   INTEGER NOT NULL,
        text      TEXT NOT NULL,
        embedding BLOB
    );
    CREATE INDEX IF NOT EXISTS rag_chunks_doc ON rag_chunks(doc_id);
    CREATE INDEX IF NOT EXISTS rag_chunks_ticker ON rag_chunks(ticker);

    CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(
        body, chunk_id UNINDEXED, ticker UNINDEXED, doc_id UNINDEXED,
        tokenize = 'porter unicode61'
    );
    """
)

_STOPWORDS = set(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "the",
        "their",
        "them",
        "they",
        "this",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "company",
        "companys",
        "s",
        "about",
        "over",
        "any",
        "there",
        "than",
        "that",
        "these",
        "those",
        "been",
        "into",
        "does",
    ]
)


SECTION_TITLES = {
    "business": "Business",
    "risk_factors": "Risk Factors",
    "mda": "MD&A",
    "market_risk": "Market Risk",
    "full_text": "Full Text",
    "prepared_remarks": "Prepared Remarks",
    "qa": "Analyst Q&A",
}


@dataclass
class DocumentMeta:
    doc_id: str
    ticker: str
    kind: str
    form: str
    title: str
    period: str | None = None
    filed: str | None = None
    url: str | None = None


def has_document(doc_id: str) -> bool:
    return db.connect().execute("SELECT 1 FROM rag_documents WHERE doc_id = ?", (doc_id,)).fetchone() is not None


def contextual_body(title: str, section_title: str, text: str) -> str:
    """Prefix chunks with where they came from; helps both BM25 and embeddings."""
    return f"{title} | {section_title}\n{text}"


def add_document(
    meta: DocumentMeta,
    chunks: list[Chunk],
    embeddings: np.ndarray | None = None,
    embed_model: str | None = None,
) -> None:
    conn = db.connect()
    with conn:
        delete_document(meta.doc_id, conn=conn, commit=False)
        conn.execute(
            "INSERT INTO rag_documents (doc_id, ticker, kind, form, title, period, filed, url, chunk_count,"
            " embed_model, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                meta.doc_id,
                meta.ticker,
                meta.kind,
                meta.form,
                meta.title,
                meta.period,
                meta.filed,
                meta.url,
                len(chunks),
                embed_model if embeddings is not None else None,
                time.time(),
            ),
        )
        for i, chunk in enumerate(chunks):
            chunk_id = f"{meta.doc_id}#{chunk.section}-{chunk.ordinal}"
            vector = embeddings[i].astype(np.float32).tobytes() if embeddings is not None else None
            conn.execute(
                "INSERT INTO rag_chunks (chunk_id, doc_id, ticker, section, ordinal, text, embedding)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (chunk_id, meta.doc_id, meta.ticker, chunk.section, chunk.ordinal, chunk.text, vector),
            )
            conn.execute(
                "INSERT INTO rag_fts (body, chunk_id, ticker, doc_id) VALUES (?, ?, ?, ?)",
                (
                    contextual_body(meta.title, SECTION_TITLES.get(chunk.section, chunk.section), chunk.text),
                    chunk_id,
                    meta.ticker,
                    meta.doc_id,
                ),
            )


def delete_document(doc_id: str, conn: sqlite3.Connection | None = None, commit: bool = True) -> None:
    conn = conn or db.connect()
    conn.execute("DELETE FROM rag_fts WHERE doc_id = ?", (doc_id,))
    conn.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))
    conn.execute("DELETE FROM rag_documents WHERE doc_id = ?", (doc_id,))
    if commit:
        conn.commit()


def list_documents(ticker: str) -> list[dict]:
    rows = (
        db.connect()
        .execute("SELECT * FROM rag_documents WHERE ticker = ? ORDER BY filed DESC, doc_id", (ticker,))
        .fetchall()
    )
    return [dict(r) for r in rows]


def get_document(doc_id: str) -> dict | None:
    row = db.connect().execute("SELECT * FROM rag_documents WHERE doc_id = ?", (doc_id,)).fetchone()
    return dict(row) if row else None


def fts_query(text: str) -> str:
    """Turn free text into a safe FTS5 OR-query (raw user text can be invalid FTS syntax)."""
    tokens = [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1 and t not in _STOPWORDS]
    seen: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.append(token)
    return " OR ".join(f'"{t}"' for t in seen[:32])


def _doc_filter(doc_ids: list[str] | None, column: str) -> tuple[str, list]:
    if not doc_ids:
        return "", []
    return f" AND {column} IN ({','.join('?' * len(doc_ids))})", list(doc_ids)


def lexical_search(ticker: str, query: str, doc_ids: list[str] | None = None, limit: int = 50) -> list[str]:
    match = fts_query(query)
    if not match:
        return []
    clause, params = _doc_filter(doc_ids, "doc_id")
    rows = (
        db.connect()
        .execute(
            f"SELECT chunk_id FROM rag_fts WHERE rag_fts MATCH ? AND ticker = ?{clause} ORDER BY bm25(rag_fts) LIMIT ?",
            [match, ticker, *params, limit],
        )
        .fetchall()
    )
    return [r["chunk_id"] for r in rows]


def dense_matrix(ticker: str, embed_model: str, doc_ids: list[str] | None = None) -> tuple[list[str], np.ndarray]:
    clause, params = _doc_filter(doc_ids, "c.doc_id")
    rows = (
        db.connect()
        .execute(
            "SELECT c.chunk_id, c.embedding FROM rag_chunks c JOIN rag_documents d ON d.doc_id = c.doc_id"
            f" WHERE c.ticker = ? AND d.embed_model = ? AND c.embedding IS NOT NULL{clause}",
            [ticker, embed_model, *params],
        )
        .fetchall()
    )
    if not rows:
        return [], np.zeros((0, 0), dtype=np.float32)
    ids = [r["chunk_id"] for r in rows]
    matrix = np.vstack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
    return ids, matrix


def get_chunks(chunk_ids: list[str]) -> dict[str, dict]:
    if not chunk_ids:
        return {}
    rows = (
        db.connect()
        .execute(
            "SELECT c.chunk_id, c.doc_id, c.section, c.ordinal, c.text, d.title, d.form, d.kind, d.period,"
            " d.filed, d.url FROM rag_chunks c JOIN rag_documents d ON d.doc_id = c.doc_id"
            f" WHERE c.chunk_id IN ({','.join('?' * len(chunk_ids))})",
            chunk_ids,
        )
        .fetchall()
    )
    return {r["chunk_id"]: dict(r) for r in rows}
