"""Retrieval quality eval: hit@1, hit@k and MRR at the section level.

    python -m evals.retrieval_eval --fixtures          # offline, synthetic corpus (used in CI)
    python -m evals.retrieval_eval AAPL MSFT --index   # real filings (needs network)

A question counts as a hit at rank r when the r-th retrieved chunk comes from one of
its expected (form, section) pairs. Section-level labels are a coarse proxy for
relevance, but they catch the regressions that matter (wrong section, TOC noise,
broken chunking) and need no hand-labelled passages.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))


def evaluate(ticker: str, questions: list[dict], k: int) -> dict:
    from app.rag import retriever

    rows = []
    for item in questions:
        expected = {tuple(e) for e in item["expect"]}
        hits = retriever.search(ticker, item["q"], k=k)
        ranks = [i + 1 for i, h in enumerate(hits) if (h.form, h.section) in expected]
        first = ranks[0] if ranks else None
        rows.append({"q": item["q"], "rank": first, "top": [f"{h.form}/{h.section}" for h in hits[:3]]})
    n = len(rows) or 1
    return {
        "ticker": ticker,
        "questions": len(rows),
        "hit@1": round(sum(r["rank"] == 1 for r in rows) / n, 3),
        f"hit@{k}": round(sum(r["rank"] is not None for r in rows) / n, 3),
        "mrr": round(sum(1 / r["rank"] for r in rows if r["rank"]) / n, 3),
        "rows": rows,
    }


def load_fixture_corpus() -> str:
    from app.rag.ingest import ingest_filing, ingest_transcript
    from app.services.edgar import extract_sections, html_to_text

    fixtures = HERE.parent / "tests" / "fixtures"
    for form, name, acc in (("10-K", "example_10k.html", "1"), ("10-Q", "example_10q.html", "2")):
        ingest_filing({
            "ticker": "EXMP", "form": form, "accessionNumber": f"0000000000-26-00000{acc}",
            "filingDate": "2026-02-01", "reportDate": "2025-12-31", "url": None,
            "sections": extract_sections(html_to_text((fixtures / name).read_text()), form),
        })
    ingest_transcript({
        "ticker": "EXMP", "year": 2026, "quarter": 1, "conferenceDate": "2026-04-20",
        "preparedRemarks": "Good afternoon and thank you for joining. Software bookings were a record this quarter "
        "and hardware demand stabilised. Given this momentum we are raising our full-year revenue guidance to 11% "
        "growth, up from our prior outlook of 9%.",
        "qaSection": "Our first question asks about tariffs on imported sensors. We expect tariffs to cost about "
        "50 basis points of hardware gross margin this year and we are qualifying a second sensor supplier.",
    })
    return "EXMP"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tickers", nargs="*")
    parser.add_argument("--fixtures", action="store_true", help="evaluate on the synthetic corpus")
    parser.add_argument("--index", action="store_true", help="index tickers before evaluating")
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--min-hit-at-k", type=float, default=None, help="exit 1 if any ticker scores below")
    parser.add_argument("--json", action="store_true", help="print full JSON results")
    args = parser.parse_args()

    if args.fixtures:
        os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="retrieval-eval-"))
        os.environ.setdefault("EMBEDDINGS", "none")

    questions = json.loads((HERE / "questions.json").read_text())
    results = []
    if args.fixtures:
        results.append(evaluate(load_fixture_corpus(), questions["fixtures"], args.k))
    for ticker in args.tickers:
        if args.index:
            from app.rag.ingest import index_ticker

            index_ticker(ticker)
        results.append(evaluate(ticker.upper(), questions["generic"], args.k))

    if not results:
        parser.error("pass --fixtures and/or tickers")

    from app.rag.embeddings import get_embedder

    embedder = get_embedder()
    print(f"retrieval: {'hybrid (' + embedder.name + ')' if embedder else 'bm25'}")
    print(f"{'ticker':<8} {'n':>3} {'hit@1':>6} {'hit@' + str(args.k):>6} {'mrr':>6}")
    for r in results:
        print(f"{r['ticker']:<8} {r['questions']:>3} {r['hit@1']:>6} {r[f'hit@{args.k}']:>6} {r['mrr']:>6}")
        for row in r["rows"]:
            if row["rank"] != 1:
                print(f"   rank={row['rank']}  {row['q']}  -> top: {', '.join(row['top'])}")
    if args.json:
        print(json.dumps(results, indent=2))
    if args.min_hit_at_k is not None and any(r[f"hit@{args.k}"] < args.min_hit_at_k for r in results):
        print(f"FAIL: hit@{args.k} below {args.min_hit_at_k}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
