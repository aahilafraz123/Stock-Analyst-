import asyncio
from types import SimpleNamespace

from app import llm
from app.rag import diff, qa
from app.rag.ingest import ingest_filing
from app.schemas import RiskChange, RiskFactorDiff
from app.services import edgar
from tests.helpers import install_fake_sources
from tests.test_rag import _filing


def test_ask_maps_citations_to_retrieved_passages(monkeypatch, fixture_text):
    ingest_filing(_filing(fixture_text))
    seen = {}

    async def cited_answer(system, documents, question, max_tokens=8000):
        seen["documents"], seen["question"] = documents, question
        blocks = [
            SimpleNamespace(
                type="text",
                text="Example Corp relies on a single supplier for specialty sensors",
                citations=[
                    SimpleNamespace(document_index=0, cited_text="available from a single supplier"),
                    SimpleNamespace(document_index=99, cited_text="bogus index is dropped"),
                ],
            ),
            SimpleNamespace(type="text", text=", which is a supply chain risk.", citations=None),
        ]
        return blocks, {"model": "claude-test", "inputTokens": 10, "outputTokens": 5}

    monkeypatch.setattr(llm, "cited_answer", cited_answer)
    result = asyncio.run(qa.ask("exmp", "Who supplies the specialty sensors?"))

    docs = seen["documents"]
    assert all(d["type"] == "document" and d["citations"] == {"enabled": True} for d in docs)
    assert docs[0]["source"]["type"] == "text" and "Risk Factors" in docs[0]["title"]
    assert seen["question"] == "Who supplies the specialty sensors?"

    assert result["ticker"] == "EXMP" and result["documents"] == 1
    first, second = result["answer"]
    assert first["citations"] == [{"source": 0, "citedText": "available from a single supplier"}]
    assert second["citations"] == []
    assert result["sources"][0]["index"] == 0 and result["sources"][0]["url"].startswith("https://www.sec.gov/")


def test_ask_with_no_matches_skips_the_llm(monkeypatch, fixture_text):
    ingest_filing(_filing(fixture_text))

    async def never(*args, **kwargs):
        raise AssertionError("LLM should not be called without passages")

    monkeypatch.setattr(llm, "cited_answer", never)
    result = asyncio.run(qa.ask("EXMP", "zzqx qqzz"))
    assert result["sources"] == [] and "No relevant passages" in result["answer"][0]["text"]


def test_risk_diff_verifies_quotes_and_caches(monkeypatch, fixture_text):
    install_fake_sources(monkeypatch, fixture_text)

    def filing(t, form, index=0):
        f = _filing(fixture_text, "10-K", f"0000000000-2{6 - index}-000001")
        f["ticker"] = t
        if index == 1:  # the older filing lacked the cybersecurity paragraph
            f["sections"]["risk_factors"] = f["sections"]["risk_factors"].split("Cybersecurity")[0] + " " * 10
        return f

    monkeypatch.setattr(edgar, "get_filing", filing)
    calls = []

    async def structured(system, content, output, max_tokens=16000):
        calls.append(content)
        real = "Cybersecurity incidents affecting our monitoring platform could expose customer data"
        result = RiskFactorDiff(
            summary="Cyber risk added.",
            added=[
                RiskChange(title="Cybersecurity", detail="New.", quote=real),
                RiskChange(title="Invented", detail="Hallucinated.", quote="We may be acquired by aliens next year"),
            ],
            removed=[],
            escalated=[],
            deemphasized=[],
        )
        return result, {"model": "claude-test"}

    monkeypatch.setattr(llm, "structured", structured)
    out = asyncio.run(diff.diff_risk_factors("EXMP"))
    assert [c["quoteVerified"] for c in out["added"]] == [True, False]
    assert out["cached"] is False and out["newer"]["accessionNumber"] != out["older"]["accessionNumber"]
    assert 'role="older"' in calls[0] and 'role="newer"' in calls[0]

    again = asyncio.run(diff.diff_risk_factors("EXMP"))
    assert again["cached"] is True and len(calls) == 1
