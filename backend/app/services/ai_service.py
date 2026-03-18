import anthropic
import os
import json
import asyncio
from dotenv import load_dotenv
from app.services.fmp_service import (
    get_company_profile,
    get_financial_ratios,
    get_competitor_ratios
)
from app.services.news_service import get_company_news, get_company_sentiment
from app.services.edgar_service import get_10q_text

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def build_full_context(ticker: str) -> dict:
    """Fetch all data sources in parallel"""

    loop = asyncio.get_event_loop()

    # Run synchronous functions in thread pool so they don't block
    profile_task = loop.run_in_executor(None, get_company_profile, ticker)
    ratios_task = loop.run_in_executor(None, get_financial_ratios, ticker)
    competitors_task = loop.run_in_executor(None, get_competitor_ratios, ticker)
    filing_task = loop.run_in_executor(None, get_10q_text, ticker)

    # Run async functions directly
    news_task = get_company_news(ticker, days_back=14)
    sentiment_task = get_company_sentiment(ticker)

    # Wait for all of them simultaneously with a timeout
    results = await asyncio.gather(
        profile_task,
        ratios_task,
        competitors_task,
        filing_task,
        news_task,
        sentiment_task,
        return_exceptions=True  # Don't fail everything if one source fails
    )

    profile, ratios, competitors, filing, news, sentiment = results

    # Handle any failed fetches gracefully
    if isinstance(filing, Exception):
        filing = None
    if isinstance(news, Exception):
        news = []
    if isinstance(sentiment, Exception):
        sentiment = None

    return {
        "profile": profile if not isinstance(profile, Exception) else None,
        "ratios": ratios if not isinstance(ratios, Exception) else None,
        "competitors": competitors if not isinstance(competitors, Exception) else None,
        "filing_excerpt": filing.get("excerpt")[:20000] if filing else None,
        "filing_date": filing.get("filingDate") if filing else None,
        "filing_sections": filing.get("sectionsFound", []) if filing else [],
        "news": news[:10] if news else [],
        "sentiment": sentiment,
    }

def run_claude_analysis(ticker: str, data: dict) -> dict:
    """Send assembled context to Claude for analysis"""

    prompt = f"""
You are a professional equity research analyst. Analyze the following data for {ticker} and produce a structured investment report.

## Company Profile
{json.dumps(data.get("profile"), indent=2)}

## Financial Ratios
{json.dumps(data.get("ratios"), indent=2)}

## Competitor Comparison
{json.dumps(data.get("competitors"), indent=2)}

## Recent News Headlines (last 14 days)
{json.dumps([n.get("headline") for n in data.get("news", [])], indent=2)}

## News Sentiment
{json.dumps(data.get("sentiment"), indent=2)}

## 10-Q Filing (filed {data.get("filing_date")}) — Sections: {data.get("filing_sections", [])}
{data.get("filing_excerpt") or "Not available"}

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

    # Strip markdown fences if present
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