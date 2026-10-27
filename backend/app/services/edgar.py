"""SEC EDGAR: filing discovery and section extraction for 10-K and 10-Q reports.

Section extraction works on "Item N." headings. Every 10-K/10-Q mentions each
item at least twice: once in the table of contents and once as the real
heading. A heading's span runs until the next item heading, so TOC entries are
a few characters long and the real section is the longest span. That rule
replaces the old fixed-window heuristic, which returned the TOC for HTML filings.
"""

import logging
import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from app.cache import DAY, HOUR, cached
from app.errors import NotFoundError
from app.net import sec_get

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
log = logging.getLogger(__name__)

SOURCE = "SEC EDGAR"

# (item number, section key, words expected near the heading)
_ITEMS = {
    "10-K": [
        ("1", "business", ("business",)),
        ("1a", "risk_factors", ("risk factors",)),
        ("7", "mda", ("management", "discussion")),
        ("7a", "market_risk", ("market risk",)),
    ],
    "10-Q": [
        ("2", "mda", ("management", "discussion")),
        ("3", "market_risk", ("market risk",)),
        ("1a", "risk_factors", ("risk factors",)),
    ],
}

# "Item 1A." / "ITEM 7 —" / "Part II, Item 1A:" at the start of a line.
_HEADING = re.compile(
    r"^[ \t]*(?:part[ \t]+[iv]{1,3}[ \t]*[,.:\-–—]?[ \t]*)?item[ \t]+(\d{1,2}[a-c]?)\b[ \t]*[\.:\-–—]?",
    re.IGNORECASE | re.MULTILINE,
)
_MIN_SECTION_CHARS = 200  # TOC entries span < ~120 chars; real sections are longer


@cached("sec.tickers", ttl=7 * DAY)
def _ticker_map() -> dict[str, str]:
    data = sec_get("https://www.sec.gov/files/company_tickers.json").json()
    return {entry["ticker"].upper(): str(entry["cik_str"]).zfill(10) for entry in data.values()}


def get_cik(ticker: str) -> str:
    mapping = _ticker_map()
    cik = mapping.get(ticker.upper()) or mapping.get(ticker.upper().replace(".", "-"))
    if not cik:
        raise NotFoundError(f"No SEC registrant found for {ticker}", source=SOURCE)
    return cik


@cached("sec.submissions", ttl=6 * HOUR)
def _submissions(cik: str) -> dict:
    data = sec_get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    recent = data.get("filings", {}).get("recent", {})
    keys = ("form", "filingDate", "reportDate", "accessionNumber", "primaryDocument")
    return {"name": data.get("name"), "recent": {k: recent.get(k, []) for k in keys}}


def list_filings(ticker: str, form: str = "10-Q", limit: int = 4) -> dict:
    """Most recent filings of one form type, newest first."""
    cik = get_cik(ticker)
    subs = _submissions(cik)
    recent = subs["recent"]
    filings = []
    for i, f in enumerate(recent["form"]):
        if f != form:
            continue
        accession = recent["accessionNumber"][i]
        filings.append(
            {
                "form": f,
                "filingDate": recent["filingDate"][i],
                "reportDate": recent["reportDate"][i] if i < len(recent["reportDate"]) else None,
                "accessionNumber": accession,
                "url": (
                    f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{accession.replace('-', '')}/{recent['primaryDocument'][i]}"
                ),
            }
        )
        if len(filings) >= limit:
            break
    return {"ticker": ticker.upper(), "cik": cik, "company": subs["name"], "filings": filings}


def html_to_text(html: bytes | str) -> str:
    """Readable plain text with line structure preserved (headings stay on their own line)."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "ix:header", "head"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = []
    for line in text.replace("\xa0", " ").replace("​", "").splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def extract_sections(text: str, form: str) -> dict[str, str]:
    headings = [(m.start(), m.end(), m.group(1).lower()) for m in _HEADING.finditer(text)]
    sections: dict[str, str] = {}
    for item, key, title_words in _ITEMS.get(form, _ITEMS["10-K"]):
        best = ""
        for idx, (start, end, number) in enumerate(headings):
            if number != item:
                continue
            title = text[end : end + 160].lower().replace("’", "'")
            if not all(word in title for word in title_words):
                continue
            stop = headings[idx + 1][0] if idx + 1 < len(headings) else len(text)
            candidate = text[start:stop].strip()
            if len(candidate) > len(best):
                best = candidate
        if len(best) >= _MIN_SECTION_CHARS:
            sections[key] = best
    return sections


@cached("sec.filing", ttl=30 * DAY)
def _fetch_filing(url: str, form: str) -> dict:
    text = html_to_text(sec_get(url, timeout=(5, 60)).content)
    sections = extract_sections(text, form)
    if not sections:
        log.warning("No item headings recognised in %s; using full text", url)
        sections = {"full_text": text[:250_000]}
    return {"sections": sections, "textLength": len(text)}


def get_filing(ticker: str, form: str = "10-Q", index: int = 0) -> dict:
    """Filing metadata plus extracted sections. `index` 0 = latest, 1 = previous, ..."""
    listing = list_filings(ticker, form, limit=index + 1)
    if len(listing["filings"]) <= index:
        raise NotFoundError(f"No {form} filing #{index + 1} found for {ticker}", source=SOURCE)
    meta = listing["filings"][index]
    body = _fetch_filing(meta["url"], form)
    return {
        "ticker": listing["ticker"],
        "company": listing["company"],
        **meta,
        "sections": body["sections"],
        "sectionsFound": list(body["sections"]),
        "textLength": body["textLength"],
    }
