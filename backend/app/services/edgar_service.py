import requests
import re
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "stockanalyzer contact@stockanalyzer.com"}

def get_cik(ticker: str):
    """Convert ticker symbol to SEC CIK number"""
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&enddt=2025-01-01&forms=10-Q"
    
    # Use the ticker-to-CIK mapping endpoint
    mapping_url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(mapping_url, headers=HEADERS)
    data = response.json()
    
    for entry in data.values():
        if entry["ticker"].upper() == ticker.upper():
            # CIK must be zero-padded to 10 digits
            return str(entry["cik_str"]).zfill(10)
    
    return None

def get_recent_10q_filings(ticker: str, limit: int = 3):
    """Get the most recent 10-Q filing metadata for a ticker"""
    cik = get_cik(ticker)
    if not cik:
        return None

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = requests.get(url, headers=HEADERS)
    data = response.json()

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accession_numbers = filings.get("accessionNumber", [])
    primary_documents = filings.get("primaryDocument", [])

    results = []
    for i, form in enumerate(forms):
        if form == "10-Q":
            accession = accession_numbers[i].replace("-", "")
            results.append({
                "form": form,
                "filingDate": dates[i],
                "accessionNumber": accession_numbers[i],
                "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_documents[i]}"
            })
        if len(results) >= limit:
            break

    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "company": data.get("name"),
        "filings": results
    }

def get_10q_text(ticker: str):
    """Get and parse the most recent 10-Q filing text"""
    filing_data = get_recent_10q_filings(ticker, limit=1)
    if not filing_data or not filing_data["filings"]:
        return None

    # Get the filing index page instead of the raw document
    accession = filing_data["filings"][0]["accessionNumber"].replace("-", "")
    cik = filing_data["cik"].lstrip("0")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{accession}-index.htm"

    response = requests.get(index_url, headers=HEADERS)
    soup = BeautifulSoup(response.content, "lxml")

    # Find the actual 10-Q document link from the index
    filing_url = None
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".htm") and "index" not in href.lower():
            filing_url = f"https://www.sec.gov{href}" if href.startswith("/") else href
            break

    if not filing_url:
        filing_url = filing_data["filings"][0]["url"]

    # Fetch and parse the actual filing
    response = requests.get(filing_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(response.content, "lxml")

    # Remove noise tags
    for tag in soup(["script", "style", "ix:header", "ix:nonfraction", "ix:nonNumeric"]):
        tag.decompose()

    # Extract meaningful text sections
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()

    # Try to find the MD&A section which is most useful for AI analysis
    mda_start = text.lower().find("management")
    if mda_start > 0:
        text = text[mda_start:]

    return {
        "ticker": ticker.upper(),
        "company": filing_data["company"],
        "filingDate": filing_data["filings"][0]["filingDate"],
        "filingUrl": filing_url,
        "excerpt": text[:8000]
    }