"""Stubs for running the research pipeline offline. All data here is synthetic."""

from app.errors import ConfigError, NotFoundError
from app.schemas import AnalysisReport
from app.services.edgar import extract_sections, html_to_text


def claim(text, *sources):
    return {"text": text, "sources": list(sources)}


def fake_report(**overrides) -> AnalysisReport:
    data = {
        "companyName": "Example Corp",
        "overallSignal": "BULLISH",
        "recommendation": "BUY",
        "confidenceScore": 140,  # out of range on purpose: must be clamped
        "summary": claim("Software mix shift is lifting margins.", "F1", "M1"),
        "valuation": {"assessment": "FAIRLY VALUED", "reasoning": "In line with peers.", "sources": ["P1"]},
        "financialHealth": {"assessment": "STRONG", "reasoning": "Net cash.", "sources": ["F2"]},
        "strengths": [claim("Software grew 31%.", "F1"), claim("Made-up support.", "Z9")],
        "risks": [claim("Single-supplier sensors.", "F2", "Q7")],
        "catalysts": [claim("Guidance raise.", "T1")],
        "competitivePosition": claim("Integrated stack.", "P1"),
        "managementTone": claim("Confident.", "T1"),
        "recentNewsImpact": claim(
            "No major news.",
        ),
        "priceContext": claim("Near highs.", "M2"),
        "analystConsensus": claim("Target implies upside.", "A1"),
        "recommendationReasoning": claim("Growth at a fair price.", "F1", "A1"),
    }
    data.update(overrides)
    return AnalysisReport.model_validate(data)


def install_fake_sources(monkeypatch, fixture_text, *, profile_error=None):
    from app.services import edgar, insider, institutional, market_data, news, transcripts

    def profile(t):
        if profile_error:
            raise profile_error
        return {"symbol": t, "companyName": "Example Corp", "currentPrice": 100.0, "description": "Widgets."}

    def filing(t, form, index=0):
        name = "example_10k.html" if form == "10-K" else "example_10q.html"
        return {
            "ticker": t,
            "company": "Example Corp",
            "form": form,
            "filingDate": "2026-02-01",
            "reportDate": "2025-12-31",
            "accessionNumber": f"0000000000-26-00000{1 if form == '10-K' else 2}",
            "url": f"https://www.sec.gov/Archives/example-{form}.htm",
            "sections": extract_sections(html_to_text(fixture_text(name)), form),
        }

    async def company_news(t, days_back=7, limit=10, with_bodies=True):
        return [
            {
                "headline": "Example Corp wins contract",
                "source": "Wire",
                "url": "https://example.com/n1",
                "datetime": "2026-10-20 12:00 UTC",
                "summary": "A contract.",
                "body": "Full body text.",
            }
        ]

    async def sentiment(t):
        raise ConfigError("FINNHUB_API_KEY is not set")

    def transcript(t):
        raise NotFoundError("No transcripts")

    monkeypatch.setattr(market_data, "get_company_profile", profile)
    monkeypatch.setattr(market_data, "get_financial_ratios", lambda t: {"peRatio": 25.0, "grossMargin": 0.46})
    monkeypatch.setattr(market_data, "get_price_context", lambda t: {"currentPrice": 100.0, "52weekHigh": 110.0})
    monkeypatch.setattr(
        market_data,
        "get_analyst_consensus",
        lambda t: {"targetMeanPrice": 120.0, "impliedUpsidePct": 20.0, "numberOfAnalysts": 12},
    )
    monkeypatch.setattr(market_data, "get_competitor_ratios", lambda t: {t: {"peRatio": 25.0}, "PEER": {"peRatio": 30}})
    monkeypatch.setattr(market_data, "get_info", lambda t: {"currentPrice": 500.0})
    monkeypatch.setattr(edgar, "get_filing", filing)
    monkeypatch.setattr(transcripts, "get_latest_earnings_transcript", transcript)
    monkeypatch.setattr(insider, "get_insider_trades", lambda t: {"summary": "Net selling.", "trades": []})
    monkeypatch.setattr(
        institutional, "get_institutional_ownership", lambda t: {"summary": "61% institutions.", "topInstitutions": []}
    )
    monkeypatch.setattr(news, "get_company_news", company_news)
    monkeypatch.setattr(news, "get_company_sentiment", sentiment)


def install_fake_llm(monkeypatch, report=None):
    from app import llm

    calls = []

    async def structured(system, content, output, max_tokens=16000):
        calls.append({"system": system, "content": content})
        usage = {
            "model": "claude-test",
            "inputTokens": 1000,
            "outputTokens": 200,
            "cacheReadTokens": 0,
            "stopReason": "end_turn",
            "latencyMs": 5,
        }
        return (report or fake_report()), usage

    monkeypatch.setattr(llm, "structured", structured)
    return calls
