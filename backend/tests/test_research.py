import asyncio

import pytest

from app.errors import NotFoundError
from app.services import history
from app.services.research import run_analysis, stream_analysis
from tests.helpers import install_fake_llm, install_fake_sources


def test_pipeline_end_to_end(monkeypatch, fixture_text):
    install_fake_sources(monkeypatch, fixture_text)
    calls = install_fake_llm(monkeypatch)

    result = asyncio.run(run_analysis("EXMP"))

    prompt = calls[0]["content"]
    assert 'id="F1"' in prompt and 'id="N1"' in prompt and 'id="A1"' in prompt
    assert "single supplier" in prompt  # retrieved risk-factor chunk made it into the evidence
    assert "Today is " in prompt

    report = result["report"]
    assert report["confidenceScore"] == 100  # clamped
    assert report["strengths"][1]["sources"] == []  # invented id Z9 stripped
    assert report["risks"][0]["sources"] == ["F2"]  # Q7 stripped, F2 kept
    cites = result["meta"]["citations"]
    # Z9 and Q7 are invented; T1 (twice) is invalid because no transcript was available.
    assert cites["invalidRemoved"] == 4
    assert report["managementTone"]["sources"] == [] and report["catalysts"][0]["sources"] == []
    # Ungrounded: Z9-only strength, uncited news claim, and the two T1-only claims.
    assert cites["groundedClaims"] == cites["claims"] - 4
    assert 0 < cites["groundedness"] < 1

    ids = {s["id"] for s in result["sources"]}
    assert {"M1", "A1", "P1", "F1", "N1"} <= ids
    assert all("text" not in s and "excerpt" in s for s in result["sources"])
    assert result["metrics"] == {
        "currentPrice": 100.0,
        "targetMeanPrice": 120.0,
        "impliedUpsidePct": 20.0,
        "numberOfAnalysts": 12,
    }

    status = {s["name"]: s["status"] for s in result["meta"]["sourceStatus"]}
    assert status["sentiment"] == "skipped" and status["transcript"] == "empty" and status["profile"] == "ok"
    assert result["meta"]["retrieval"]["mode"] == "bm25" and result["meta"]["retrieval"]["chunks"] > 0
    assert result["meta"]["benchmarkPrice"] == 500.0
    assert result["meta"]["reportId"]


def test_recent_report_is_served_from_history(monkeypatch, fixture_text):
    install_fake_sources(monkeypatch, fixture_text)
    calls = install_fake_llm(monkeypatch)
    first = asyncio.run(run_analysis("EXMP"))
    second = asyncio.run(run_analysis("EXMP"))
    assert len(calls) == 1
    assert second["meta"]["cached"] is True and second["meta"]["reportId"] == first["meta"]["reportId"]
    asyncio.run(run_analysis("EXMP", refresh=True))
    assert len(calls) == 2
    assert len(history.list_reports("EXMP")) == 2


def test_unknown_ticker_fails_fast(monkeypatch, fixture_text):
    install_fake_sources(monkeypatch, fixture_text, profile_error=NotFoundError("Ticker ZZZZ not found"))
    calls = install_fake_llm(monkeypatch)
    with pytest.raises(NotFoundError):
        asyncio.run(run_analysis("ZZZZ"))
    assert calls == []


def test_stream_emits_progress_then_report(monkeypatch, fixture_text):
    install_fake_sources(monkeypatch, fixture_text)
    install_fake_llm(monkeypatch)

    async def collect():
        return [e async for e in stream_analysis("EXMP")]

    events = asyncio.run(collect())
    stages = [e["stage"] for e in events if e["type"] == "stage"]
    assert stages == ["sources", "indexing", "retrieval", "llm"]
    assert [e["phase"] for e in events if e["type"] == "llm"] == ["thinking", "writing"]
    finals = [e for e in events if e["type"] == "source" and e["status"] != "pending"]
    assert len(finals) == 13
    assert events[-1]["type"] == "report" and events[-1]["data"]["ticker"] == "EXMP"


def test_stream_reports_errors_as_events(monkeypatch, fixture_text):
    install_fake_sources(monkeypatch, fixture_text, profile_error=NotFoundError("Ticker ZZZZ not found"))
    install_fake_llm(monkeypatch)

    async def collect():
        return [e async for e in stream_analysis("ZZZZ")]

    last = asyncio.run(collect())[-1]
    assert last == {"type": "error", "status": 404, "error": "not_found", "detail": "Ticker ZZZZ not found"}


def test_hung_source_times_out_without_blocking_the_report(monkeypatch, fixture_text):
    import time as _time

    from app.services import insider, research

    install_fake_sources(monkeypatch, fixture_text)
    install_fake_llm(monkeypatch)
    monkeypatch.setattr(research, "SOURCE_TIMEOUT", 0.2)
    monkeypatch.setattr(insider, "get_insider_trades", lambda t: _time.sleep(1) or {"summary": "late"})
    result = asyncio.run(run_analysis("EXMP"))
    status = {s["name"]: s for s in result["meta"]["sourceStatus"]}
    assert status["insider"]["status"] == "error" and "timed out" in status["insider"]["detail"]
    assert result["report"]["recommendation"] == "BUY"
