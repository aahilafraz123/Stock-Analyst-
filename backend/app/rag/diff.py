"""Year-over-year 10-K risk factor diff: what was added, dropped, escalated or softened.

Each change carries a verbatim quote; we check the quote really appears in the
filing it claims to come from and flag any that don't (a cheap hallucination check).
"""

import asyncio
import re

from app import cache, llm
from app.errors import NotFoundError
from app.schemas import RiskFactorDiff
from app.services import edgar

MAX_SECTION_CHARS = 200_000  # ~50k tokens per filing; risk factors rarely exceed this

DIFF_SYSTEM = """You are an equity analyst comparing the Risk Factors sections of two consecutive annual
reports (10-K) from the same company. Identify substantive changes only: new risks, removed risks, and risks
whose severity or specificity materially changed. Ignore reordering, renumbering and boilerplate edits.
Quotes must be copied verbatim from the filing named."""


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


def quote_found(quote: str, text: str) -> bool:
    q = _normalise(quote).strip(" .…\"'")
    if len(q) < 12:
        return False
    hay = _normalise(text)
    # Allow ellipses inside quotes: every fragment must appear, in order.
    pos = 0
    for frag in (f.strip() for f in re.split(r"\.{3}|…", q)):
        if not frag:
            continue
        idx = hay.find(frag, pos)
        if idx == -1:
            return False
        pos = idx + len(frag)
    return True


async def diff_risk_factors(ticker: str) -> dict:
    ticker = ticker.upper()
    new, old = await asyncio.gather(
        asyncio.to_thread(edgar.get_filing, ticker, "10-K", 0),
        asyncio.to_thread(edgar.get_filing, ticker, "10-K", 1),
    )
    new_text, old_text = new["sections"].get("risk_factors"), old["sections"].get("risk_factors")
    if not new_text or not old_text:
        raise NotFoundError(f"Could not locate Risk Factors in both of {ticker}'s last two 10-Ks", source="SEC EDGAR")

    key = f"riskdiff:{new['accessionNumber']}:{old['accessionNumber']}"
    if (hit := cache.get(key)) is not None:
        return {**hit, "cached": True}

    truncated = len(new_text) > MAX_SECTION_CHARS or len(old_text) > MAX_SECTION_CHARS
    prompt = (
        f'<filing role="older" form="10-K" filed="{old["filingDate"]}">\n{old_text[:MAX_SECTION_CHARS]}\n</filing>\n\n'
        f'<filing role="newer" form="10-K" filed="{new["filingDate"]}">\n{new_text[:MAX_SECTION_CHARS]}\n</filing>\n\n'
        f"Compare the Risk Factors of {ticker}'s newer 10-K against the older one. For removed risks quote the "
        "older filing; for everything else quote the newer filing."
    )
    diff, usage = await llm.structured(DIFF_SYSTEM, prompt, RiskFactorDiff)

    def annotate(changes, source_text):
        return [{**c.model_dump(), "quoteVerified": quote_found(c.quote, source_text)} for c in changes]

    result = {
        "ticker": ticker,
        "newer": {k: new[k] for k in ("filingDate", "reportDate", "url", "accessionNumber")},
        "older": {k: old[k] for k in ("filingDate", "reportDate", "url", "accessionNumber")},
        "summary": diff.summary,
        "added": annotate(diff.added, new_text),
        "removed": annotate(diff.removed, old_text),
        "escalated": annotate(diff.escalated, new_text),
        "deemphasized": annotate(diff.deemphasized, new_text),
        "truncated": truncated,
        "meta": usage,
    }
    cache.set(key, result, ttl=90 * cache.DAY)  # both filings are immutable
    return {**result, "cached": False}
