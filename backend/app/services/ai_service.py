import anthropic
import os
import json
import asyncio
from dotenv import load_dotenv
from app.services.fmp_service import (
    get_company_profile,
    get_financial_ratios,
    get_competitor_ratios,
    get_price_context,
    get_analyst_consensus
)
from app.services.news_service import get_company_news, get_company_sentiment
from app.services.edgar_service import get_10q_text, get_10k_text

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def build_full_context(ticker: str) -> dict:
    """Fetch all data sources in parallel"""

    loop = asyncio.get_event_loop()

    profile_task      = loop.run_in_executor(None, get_company_profile, ticker)
    ratios_task       = loop.run_in_executor(None, get_financial_ratios, ticker)
    competitors_task  = loop.run_in_executor(None, get_competitor_ratios, ticker)
    price_task        = loop.run_in_executor(None, get_price_context, ticker)
    analyst_task      = loop.run_in_executor(None, get_analyst_consensus, ticker)
    filing_10q_task   = loop.run_in_executor(None, get_10q_text, ticker)
    filing_10k_task   = loop.run_in_executor(None, get_10k_text, ticker)

    news_task      = get_company_news(ticker, days_back=14)
    sentiment_task = get_company_sentiment(ticker)

    results = await asyncio.gather(
        profile_task,
        ratios_task,
        competitors_task,
        price_task,
        analyst_task,
        filing_10q_task,
        filing_10k_task,
        news_task,
        sentiment_task,
        return_exceptions=True
    )

    (profile, ratios, competitors, price_context,
     analyst, filing_10q, filing_10k, news, sentiment) = results

    def safe(val):
        return None if isinstance(val, Exception) else val

    filing_10q = safe(filing_10q)
    filing_10k = safe(filing_10k)

    return {
        "profile":              safe(profile),
        "ratios":               safe(ratios),
        "competitors":          safe(competitors),
        "price_context":        safe(price_context),
        "analyst_consensus":    safe(analyst),
        "filing_10q_excerpt":   filing_10q.get("excerpt", "")[:20000] if filing_10q else None,
        "filing_10q_date":      filing_10q.get("filingDate") if filing_10q else None,
        "filing_10q_sections":  filing_10q.get("sectionsFound", []) if filing_10q else [],
        "filing_10k_excerpt":   filing_10k.get("excerpt", "")[:15000] if filing_10k else None,
        "filing_10k_date":      filing_10k.get("filingDate") if filing_10k else None,
        "filing_10k_sections":  filing_10k.get("sectionsFound", []) if filing_10k else [],
        "news":                 (safe(news) or [])[:10],
        "sentiment":            safe(sentiment),
    }

def run_claude_analysis(ticker: str, data: dict) -> dict:
    """Send assembled context to Claude for analysis"""

    prompt = f"""
You are a professional equity research analyst. Analyze the following data for {ticker} and produce a structured investment report.

## Company Profile
{json.dumps(data.get("profile"), indent=2)}

## Financial Ratios
{json.dumps(data.get("ratios"), indent=2)}

## Price Context & Momentum
{json.dumps(data.get("price_context"), indent=2)}

## Wall Street Analyst Consensus
{json.dumps(data.get("analyst_consensus"), indent=2)}

## Competitor Comparison
{json.dumps(data.get("competitors"), indent=2)}

## Recent News Articles (last 14 days)
{json.dumps([{
    "headline": n.get("headline"),
    "source": n.get("source"),
    "datetime": n.get("datetime"),
    "body": n.get("body") or n.get("summary") or ""
} for n in data.get("news", [])], indent=2)}

## News Sentiment
{json.dumps(data.get("sentiment"), indent=2)}

## 10-Q Filing (filed {data.get("filing_10q_date")}) — Sections: {data.get("filing_10q_sections")}
{data.get("filing_10q_excerpt") or "Not available"}

## 10-K Annual Report (filed {data.get("filing_10k_date")}) — Sections: {data.get("filing_10k_sections")}
{data.get("filing_10k_excerpt") or "Not available"}

---

Based on all of the above, provide a structured analysis in the following JSON format exactly:

{{
  "ticker": "{ticker}",
  "companyName": "...",
  "analysisDate": "today's date",
  "overallSignal": "BULLISH" or "BEARISH" or "NEUTRAL",
  "confidenceScore": 0-100,
  "summary": "2-3 sentence executive summary",
  "valuation": {{
    "assessment": "UNDERVALUED" or "FAIRLY VALUED" or "OVERVALUED",
    "reasoning": "2-3 sentences"
  }},
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "risks": ["risk 1", "risk 2", "risk 3"],
  "competitivePosition": "2-3 sentences on how they compare to peers",
  "recentNewsImpact": "1-2 sentences on how recent news affects outlook",
  "financialHealth": {{
    "assessment": "STRONG" or "MODERATE" or "WEAK",
    "reasoning": "2-3 sentences"
  }},
  "priceContext": "1-2 sentences on price momentum and where stock sits vs 52 week range",
  "analystConsensus": "1-2 sentences summarizing what Wall Street thinks including mean target price",
  "recommendation": "BUY" or "HOLD" or "SELL",
  "recommendationReasoning": "2-3 sentences explaining the recommendation"
}}

Return ONLY the JSON object, no extra text, no markdown fences.
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())

async def analyze_stock(ticker: str) -> dict:
    """Main entry point — fetch all data then analyze"""
    print(f"[{ticker}] Fetching all data in parallel...")
    data = await build_full_context(ticker)

    print(f"[{ticker}] Running Claude analysis...")
    result = run_claude_analysis(ticker, data)

    return result