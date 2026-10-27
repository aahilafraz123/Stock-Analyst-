"""Earnings call transcripts via the earningscall library.

Level-4 transcripts come pre-split into prepared remarks and Q&A (paid plans);
otherwise we fetch the plain text and split on common operator phrases.
"""

import logging
import re
from datetime import UTC, datetime

import earningscall

from app.cache import DAY, cached
from app.config import settings
from app.errors import NotFoundError

log = logging.getLogger(__name__)

SOURCE = "earningscall"

if settings.earningscall_api_key:
    earningscall.api_key = settings.earningscall_api_key

_QA_MARKERS = (
    "question-and-answer session",
    "question-and-answer",
    "question and answer session",
    "question and answer",
    "q&a session",
    "we will now begin the question",
    "we'll now open the call",
    "open the floor to questions",
    "open the line for questions",
    "open the lines for questions",
    "open the call to questions",
    "open the call for questions",
    "our first question",
    "take your first question",
    "first question comes from",
    "first question today",
)


def split_prepared_and_qa(text: str) -> tuple[str, str]:
    lower = text.lower()
    positions = [lower.find(m) for m in _QA_MARKERS]
    positions = [p for p in positions if p > 1000]  # require meaningful prepared remarks
    if not positions:
        return text, ""
    cut = min(positions)
    # Start Q&A at the beginning of the operator's sentence, not mid-sentence.
    sentence_start = max(text.rfind(". ", 0, cut), text.rfind("? ", 0, cut))
    if sentence_start != -1 and cut - sentence_start < 200:
        cut = sentence_start + 2
    return text[:cut].strip(), text[cut:].strip()


def _conference_ts(event) -> float:
    date = getattr(event, "conference_date", None)
    if date is None:
        return 0.0
    if date.tzinfo is None:
        date = date.replace(tzinfo=UTC)
    return date.timestamp()


def _fetch_one(company, event) -> dict | None:
    prepared = qa = ""
    try:
        t = company.get_transcript(event=event, level=4)
        if t and t.prepared_remarks:
            prepared, qa = t.prepared_remarks, t.questions_and_answers or ""
    except Exception as exc:  # level 4 needs a paid key
        log.debug("Level-4 transcript unavailable: %s", exc)
    if not prepared:
        t = company.get_transcript(event=event)
        if not t or not t.text:
            return None
        prepared, qa = split_prepared_and_qa(re.sub(r"\s+", " ", t.text).strip())
    return {
        "year": event.year,
        "quarter": event.quarter,
        "conferenceDate": str(event.conference_date)[:10] if event.conference_date else None,
        "preparedRemarks": prepared,
        "qaSection": qa,
        "length": len(prepared) + len(qa),
    }


@cached("transcripts", ttl=3 * DAY)
def get_transcripts(ticker: str, limit: int = 1) -> list[dict]:
    """Most recent `limit` earnings call transcripts, newest first."""
    company = earningscall.get_company(ticker.lower())
    if not company:
        raise NotFoundError(f"No earnings calls available for {ticker}", source=SOURCE)
    now = datetime.now(UTC).timestamp()
    events = sorted((e for e in company.events() if 0 < _conference_ts(e) < now), key=_conference_ts, reverse=True)
    results = []
    for event in events:
        if len(results) >= limit:
            break
        try:
            if item := _fetch_one(company, event):
                results.append({"ticker": ticker.upper(), **item})
        except Exception as exc:
            log.info("Transcript %s Q%s %s failed: %s", ticker, event.quarter, event.year, exc)
    if not results:
        raise NotFoundError(f"No transcripts retrievable for {ticker}", source=SOURCE)
    return results


def get_latest_earnings_transcript(ticker: str) -> dict:
    return get_transcripts(ticker, limit=1)[0]
