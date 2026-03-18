import requests
import re
import io
import pdfplumber
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "stockanalyzer contact@stockanalyzer.com"}

def get_cik(ticker: str):
    """Convert ticker symbol to SEC CIK number"""
    mapping_url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(mapping_url, headers=HEADERS)
    data = response.json()

    for entry in data.values():
        if entry["ticker"].upper() == ticker.upper():
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

def find_pdf_url(cik: str, accession: str):
    """Look through the filing index to find a PDF version of the 10-Q"""
    cik_int = int(cik)
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{accession}-index.htm"
    
    response = requests.get(index_url, headers=HEADERS)
    soup = BeautifulSoup(response.content, "lxml")

    # Look for a PDF file in the filing index
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.lower().endswith(".pdf"):
            return f"https://www.sec.gov{href}" if href.startswith("/") else href

    return None

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF using pdfplumber"""
    text_parts = []
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    
    return "\n".join(text_parts)

def extract_key_sections(full_text: str) -> dict:
    """
    Extract the most investment-relevant sections from the 10-Q text.
    These sections appear consistently across all company 10-Q filings.
    """
    text_lower = full_text.lower()
    sections = {}

    # Define the sections we want and what to search for
    section_markers = [
        ("mda", [
            "management's discussion and analysis",
            "management discussion and analysis",
            "management's discussion"
        ]),
        ("risk_factors", [
            "risk factors",
            "item 1a"
        ]),
        ("liquidity", [
            "liquidity and capital resources",
            "liquidity"
        ]),
        ("results_of_operations", [
            "results of operations",
            "results from operations"
        ]),
    ]

    for section_name, markers in section_markers:
        for marker in markers:
            idx = text_lower.find(marker)
            if idx != -1:
                # Extract up to 8000 chars per section
                sections[section_name] = full_text[idx:idx + 8000].strip()
                break

    return sections

def get_10q_text(ticker: str):
    """
    Main function — finds the 10-Q, extracts text from PDF if available,
    falls back to HTML parsing if no PDF exists.
    """
    filing_data = get_recent_10q_filings(ticker, limit=1)
    if not filing_data or not filing_data["filings"]:
        return None

    accession = filing_data["filings"][0]["accessionNumber"].replace("-", "")
    cik = filing_data["cik"]

    # Try to find and use a PDF version first
    pdf_url = find_pdf_url(cik, accession)
    
    if pdf_url:
        print(f"[{ticker}] Found PDF filing, extracting text...")
        response = requests.get(pdf_url, headers=HEADERS, timeout=60)
        
        if response.status_code == 200:
            full_text = extract_text_from_pdf(response.content)
            sections = extract_key_sections(full_text)

            # Build a structured excerpt from the key sections
            excerpt_parts = []
            
            if sections.get("mda"):
                excerpt_parts.append("=== MANAGEMENT DISCUSSION & ANALYSIS ===\n" + sections["mda"])
            if sections.get("results_of_operations"):
                excerpt_parts.append("=== RESULTS OF OPERATIONS ===\n" + sections["results_of_operations"])
            if sections.get("liquidity"):
                excerpt_parts.append("=== LIQUIDITY & CAPITAL RESOURCES ===\n" + sections["liquidity"])
            if sections.get("risk_factors"):
                excerpt_parts.append("=== RISK FACTORS ===\n" + sections["risk_factors"])

            excerpt = "\n\n".join(excerpt_parts)

            # If we got good content return it
            if len(excerpt) > 500:
                return {
                    "ticker": ticker.upper(),
                    "company": filing_data["company"],
                    "filingDate": filing_data["filings"][0]["filingDate"],
                    "filingUrl": pdf_url,
                    "source": "pdf",
                    "sectionsFound": list(sections.keys()),
                    "excerpt": excerpt[:20000]  # ~15k tokens, fits well in Claude's context
                }

    # Fallback to HTML parsing if no PDF found
    print(f"[{ticker}] No PDF found, falling back to HTML parsing...")
    cik_int = int(cik)
    accession_clean = accession
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_clean}/{accession_clean}-index.htm"

    response = requests.get(index_url, headers=HEADERS)
    soup = BeautifulSoup(response.content, "lxml")

    filing_url = None
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".htm") and "index" not in href.lower():
            filing_url = f"https://www.sec.gov{href}" if href.startswith("/") else href
            break

    if not filing_url:
        filing_url = filing_data["filings"][0]["url"]

    response = requests.get(filing_url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(response.content, "lxml")

    for tag in soup(["script", "style", "ix:header"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()
    sections = extract_key_sections(text)

    excerpt_parts = []
    if sections.get("mda"):
        excerpt_parts.append("=== MANAGEMENT DISCUSSION & ANALYSIS ===\n" + sections["mda"])
    if sections.get("results_of_operations"):
        excerpt_parts.append("=== RESULTS OF OPERATIONS ===\n" + sections["results_of_operations"])
    if sections.get("liquidity"):
        excerpt_parts.append("=== LIQUIDITY & CAPITAL RESOURCES ===\n" + sections["liquidity"])
    if sections.get("risk_factors"):
        excerpt_parts.append("=== RISK FACTORS ===\n" + sections["risk_factors"])

    excerpt = "\n\n".join(excerpt_parts) if excerpt_parts else text[:8000]

    return {
        "ticker": ticker.upper(),
        "company": filing_data["company"],
        "filingDate": filing_data["filings"][0]["filingDate"],
        "filingUrl": filing_url,
        "source": "html",
        "sectionsFound": list(sections.keys()),
        "excerpt": excerpt[:20000]
    }
