"""Hybrid retrieval: BM25 (FTS5) + dense cosine similarity, fused with Reciprocal Rank Fusion."""

import logging
from dataclasses import asdict, dataclass

import numpy as np

from app.rag import store
from app.rag.embeddings import get_embedder

log = logging.getLogger(__name__)

RRF_K = 60  # standard constant from Cormack et al. (2009)
CANDIDATES = 50


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    section: str
    text: str
    score: float
    title: str
    form: str
    kind: str
    period: str | None
    filed: str | None
    url: str | None
    lexical_rank: int | None = None
    dense_rank: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def rrf(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    return scores


def _dense_ranking(ticker: str, query: str, doc_ids: list[str] | None) -> list[str]:
    embedder = get_embedder()
    if embedder is None:
        return []
    ids, matrix = store.dense_matrix(ticker, embedder.name, doc_ids)
    if not ids:
        return []
    try:
        q = embedder.embed([query], kind="query")[0]
    except Exception as exc:
        log.warning("Query embedding failed, falling back to BM25: %s", exc)
        return []
    sims = matrix @ q
    order = np.argsort(-sims)[:CANDIDATES]
    return [ids[i] for i in order]


def search(ticker: str, query: str, k: int = 6, doc_ids: list[str] | None = None) -> list[Hit]:
    ticker = ticker.upper()
    lexical = store.lexical_search(ticker, query, doc_ids, limit=CANDIDATES)
    dense = _dense_ranking(ticker, query, doc_ids)
    scores = rrf([r for r in (lexical, dense) if r])
    top = sorted(scores, key=scores.get, reverse=True)[:k]
    rows = store.get_chunks(top)
    lex_rank = {c: i + 1 for i, c in enumerate(lexical)}
    dense_rank = {c: i + 1 for i, c in enumerate(dense)}
    hits = []
    for chunk_id in top:
        row = rows.get(chunk_id)
        if not row:
            continue
        hits.append(
            Hit(
                chunk_id=chunk_id,
                doc_id=row["doc_id"],
                section=row["section"],
                text=row["text"],
                score=round(scores[chunk_id], 5),
                title=row["title"],
                form=row["form"],
                kind=row["kind"],
                period=row["period"],
                filed=row["filed"],
                url=row["url"],
                lexical_rank=lex_rank.get(chunk_id),
                dense_rank=dense_rank.get(chunk_id),
            )
        )
    return hits


def multi_search(
    ticker: str, queries: dict[str, str], k_per_query: int = 4, doc_ids: list[str] | None = None
) -> dict[str, list[Hit]]:
    """Run several topic queries; each chunk is assigned to the first topic that retrieves it."""
    seen: set[str] = set()
    results: dict[str, list[Hit]] = {}
    for topic, query in queries.items():
        hits = [h for h in search(ticker, query, k=k_per_query + 3, doc_ids=doc_ids) if h.chunk_id not in seen]
        results[topic] = hits[:k_per_query]
        seen.update(h.chunk_id for h in results[topic])
    return results
