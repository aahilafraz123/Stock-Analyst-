import numpy as np

from app.rag import retriever, store
from app.rag.chunking import MIN_CHARS, TARGET_CHARS, chunk_text
from app.rag.ingest import ingest_filing, ingest_transcript
from app.services.edgar import extract_sections, html_to_text


def _filing(fixture_text, form="10-K", accession="0000000000-26-000001"):
    name = "example_10k.html" if form == "10-K" else "example_10q.html"
    return {
        "ticker": "EXMP",
        "form": form,
        "accessionNumber": accession,
        "filingDate": "2026-02-01",
        "reportDate": "2025-12-31",
        "url": f"https://www.sec.gov/Archives/example/{accession}.htm",
        "sections": extract_sections(html_to_text(fixture_text(name)), form),
    }


TRANSCRIPT = {
    "ticker": "EXMP",
    "year": 2026,
    "quarter": 1,
    "conferenceDate": "2026-04-20",
    "preparedRemarks": "Good afternoon. "
    + "Software bookings were a record this quarter. " * 20
    + "We are raising our full-year revenue guidance to 11% growth.",
    "qaSection": "Our first question comes from an analyst asking about tariffs. "
    + "We expect tariffs on sensors to cost about 50 basis points of hardware margin. " * 10,
}


class FakeEmbedder:
    """Deterministic bag-of-words embedder so the dense path can be tested offline."""

    name = "fake:bow"
    vocab = ("cash", "liquidity", "debt", "competition", "supplier", "tariff", "guidance", "revenue", "margin")

    def embed(self, texts, kind):
        rows = []
        for t in texts:
            t = t.lower()
            rows.append([t.count(w) + 0.01 for w in self.vocab])
        v = np.array(rows, dtype=np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_chunks_respect_size_and_overlap():
    paragraphs = [f"Paragraph {i}. " + "word " * 60 for i in range(30)]
    chunks = chunk_text("\n".join(paragraphs), "mda")
    assert len(chunks) > 3
    assert all(len(c.text) <= TARGET_CHARS + 400 for c in chunks)
    assert all(len(c.text) >= MIN_CHARS for c in chunks)
    # consecutive chunks overlap, even when paragraphs are longer than the overlap window
    assert chunks[0].text[-100:] in chunks[1].text
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_single_huge_line_is_split_on_sentences():
    text = "This is a sentence about revenue growth. " * 200  # transcripts arrive as one line
    chunks = chunk_text(text, "prepared_remarks")
    assert len(chunks) > 3
    assert all(c.text.endswith(".") for c in chunks)


def test_fts_query_is_sanitised():
    assert store.fts_query('What is "cash"? (AND) OR -debt*') == '"cash" OR "debt"'
    assert store.fts_query("the of and") == ""


def test_rrf_rewards_agreement():
    scores = retriever.rrf([["a", "b", "c"], ["b", "a", "d"]])
    assert max(scores, key=scores.get) in ("a", "b")
    assert scores["b"] > scores["c"] and scores["a"] > scores["d"]


def test_ingest_and_lexical_search(fixture_text):
    doc_id = ingest_filing(_filing(fixture_text))
    assert store.has_document(doc_id)
    hits = retriever.search("EXMP", "single supplier for specialty sensors", k=3)
    assert hits and hits[0].section == "risk_factors"
    assert "single supplier" in hits[0].text
    hits = retriever.search("exmp", "cash repurchased debt liquidity", k=3)
    assert hits[0].section == "mda"
    assert hits[0].url.startswith("https://www.sec.gov/")


def test_ingest_is_idempotent(fixture_text):
    filing = _filing(fixture_text)
    ingest_filing(filing)
    ingest_filing(filing)
    docs = store.list_documents("EXMP")
    assert len(docs) == 1 and docs[0]["chunk_count"] > 0


def test_doc_filter_and_multi_search_dedupes(fixture_text):
    k_id = ingest_filing(_filing(fixture_text))
    q_id = ingest_filing(_filing(fixture_text, "10-Q", "0000000000-26-000002"))
    t_id = ingest_transcript(TRANSCRIPT)
    only_q = retriever.search("EXMP", "revenue software", k=10, doc_ids=[q_id])
    assert only_q and {h.doc_id for h in only_q} == {q_id}

    topics = {"a": "revenue growth software", "b": "revenue growth software subscriptions"}
    results = retriever.multi_search("EXMP", topics, k_per_query=2, doc_ids=[k_id, q_id, t_id])
    ids = [h.chunk_id for hits in results.values() for h in hits]
    assert len(ids) == len(set(ids))

    calls = retriever.search("EXMP", "tariffs hardware margin guidance", k=3, doc_ids=[t_id])
    assert calls[0].kind == "transcript"


def test_hybrid_search_uses_dense_ranking(fixture_text, monkeypatch):
    fake = FakeEmbedder()
    monkeypatch.setattr("app.rag.ingest.get_embedder", lambda: fake)
    monkeypatch.setattr("app.rag.retriever.get_embedder", lambda: fake)
    ingest_filing(_filing(fixture_text))
    docs = store.list_documents("EXMP")
    assert docs[0]["embed_model"] == "fake:bow"
    hits = retriever.search("EXMP", "liquidity cash debt", k=3)
    assert hits[0].dense_rank is not None
    assert hits[0].section == "mda"
