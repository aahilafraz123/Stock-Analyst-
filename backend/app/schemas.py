"""Pydantic models for Claude's structured output.

These double as the JSON schema sent to the API (see llm.strict_schema), so the
field descriptions are instructions to the model as much as documentation.
"""

from typing import Literal

from pydantic import BaseModel, Field

SourceIds = list[str]
_SOURCES = "IDs of the evidence blocks that support this, e.g. ['F3', 'T1']. Never invent IDs."


class Claim(BaseModel):
    text: str = Field(description="One specific, evidence-backed point (1-2 sentences, cite figures).")
    sources: SourceIds = Field(description=_SOURCES)


class Narrative(BaseModel):
    text: str = Field(description="2-3 sentences.")
    sources: SourceIds = Field(description=_SOURCES)


class Valuation(BaseModel):
    assessment: Literal["UNDERVALUED", "FAIRLY VALUED", "OVERVALUED"]
    reasoning: str = Field(description="2-3 sentences comparing multiples to peers, growth and history.")
    sources: SourceIds = Field(description=_SOURCES)


class FinancialHealth(BaseModel):
    assessment: Literal["STRONG", "MODERATE", "WEAK"]
    reasoning: str = Field(description="2-3 sentences on balance sheet, cash generation and margins.")
    sources: SourceIds = Field(description=_SOURCES)


class AnalysisReport(BaseModel):
    companyName: str
    overallSignal: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    recommendation: Literal["BUY", "HOLD", "SELL"]
    confidenceScore: int = Field(
        description="0-100. Reflects how complete and consistent the evidence is, not how bullish you are."
    )
    summary: Narrative = Field(description="Executive summary of the investment case.")
    valuation: Valuation
    financialHealth: FinancialHealth
    strengths: list[Claim] = Field(description="3-5 strengths.")
    risks: list[Claim] = Field(description="3-5 risks, most material first.")
    catalysts: list[Claim] = Field(description="1-3 upcoming events or developments that could move the stock.")
    competitivePosition: Narrative
    managementTone: Narrative = Field(
        description="What the earnings call reveals: confidence, hedging, guidance changes, analyst pushback."
    )
    recentNewsImpact: Narrative
    priceContext: Narrative = Field(description="Momentum and position within the 52-week range.")
    analystConsensus: Narrative = Field(description="Wall Street view, including the mean price target.")
    recommendationReasoning: Narrative


class RiskChange(BaseModel):
    title: str = Field(description="Short name for the risk.")
    detail: str = Field(description="1-2 sentences on what changed and why it matters to investors.")
    quote: str = Field(
        description="A short verbatim excerpt (under 300 characters) from the relevant filing that shows the change."
    )


class RiskFactorDiff(BaseModel):
    summary: str = Field(description="3-4 sentence overview of how the risk profile shifted year over year.")
    added: list[RiskChange] = Field(description="Risks that appear in the newer filing but not the older one.")
    removed: list[RiskChange] = Field(description="Risks dropped from the newer filing. Quote the older filing.")
    escalated: list[RiskChange] = Field(description="Existing risks described with materially more severity or detail.")
    deemphasized: list[RiskChange] = Field(description="Existing risks that were softened or shortened.")
