"""Summarise citation quality across stored reports (no API calls).

    python -m evals.report_eval

For each report: share of claims with at least one valid citation (groundedness),
invented citation IDs that were stripped, and which evidence types were cited.
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402
from app.services import history  # noqa: E402,F401  (registers the reports table)


def main() -> int:
    rows = db.connect().execute("SELECT id, ticker, model, payload FROM reports ORDER BY created_at").fetchall()
    if not rows:
        print("No stored reports yet. Run an analysis first.")
        return 0
    print(f"{'id':>4} {'ticker':<7} {'model':<20} {'claims':>6} {'grounded':>8} {'invalid':>7}  cited kinds")
    totals = Counter()
    for row in rows:
        payload = json.loads(row["payload"])
        cites = payload["meta"].get("citations", {})
        kinds = Counter()
        report = payload["report"]
        for value in report.values():
            items = value if isinstance(value, list) else [value]
            for item in items:
                if isinstance(item, dict):
                    kinds.update(sid.rstrip("0123456789") for sid in item.get("sources", []))
        totals.update({"claims": cites.get("claims", 0), "grounded": cites.get("groundedClaims", 0),
                       "invalid": cites.get("invalidRemoved", 0), "total": cites.get("total", 0)})
        print(f"{row['id']:>4} {row['ticker']:<7} {row['model'] or '?':<20} {cites.get('claims', 0):>6} "
              f"{cites.get('groundedness') or 0:>8.0%} {cites.get('invalidRemoved', 0):>7}  "
              + " ".join(f"{k}:{v}" for k, v in sorted(kinds.items())))
    if totals["claims"]:
        print(f"\noverall groundedness {totals['grounded'] / totals['claims']:.1%}, "
              f"invalid citation rate {totals['invalid'] / max(totals['total'], 1):.1%} over {len(rows)} reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
