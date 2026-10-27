import json

import pytest
from fastapi.testclient import TestClient

from app.errors import UpstreamError
from app.main import app
from app.services import history, market_data
from tests.helpers import install_fake_llm, install_fake_sources

ORIGIN = {"Origin": "http://localhost:5173"}


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["retrieval"] == "bm25"
    assert set(body["configured"]) == {"anthropic", "finnhub", "earningscall", "voyage"}


@pytest.mark.parametrize("path", ["/stocks/bad!!/profile", "/stocks/TOOLONGTICKER1/ratios", "/analysis/$$$"])
def test_invalid_ticker_is_422(client, path):
    response = client.get(path, headers=ORIGIN)
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_input"


def test_upstream_failure_is_json_502_with_cors(client, monkeypatch):
    def boom(ticker):
        raise UpstreamError("Yahoo Finance is unreachable", source="Yahoo Finance")

    monkeypatch.setattr(market_data, "get_company_profile", boom)
    response = client.get("/stocks/AAPL/profile", headers=ORIGIN)
    assert response.status_code == 502
    assert response.json() == {
        "error": "upstream_error",
        "detail": "Yahoo Finance is unreachable",
        "source": "Yahoo Finance",
    }
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unexpected_exception_is_json_500_with_cors(client, monkeypatch):
    def boom(ticker):
        raise ZeroDivisionError("oops")

    monkeypatch.setattr(market_data, "get_financial_ratios", boom)
    response = client.get("/stocks/AAPL/ratios", headers=ORIGIN)
    assert response.status_code == 500
    assert response.json()["error"] == "internal_error"
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_missing_key_is_503(client):
    response = client.get("/news/AAPL")
    assert response.status_code == 503 and "FINNHUB_API_KEY" in response.json()["detail"]


def test_snapshot_lowercase_ticker(client, monkeypatch):
    monkeypatch.setattr(
        market_data,
        "get_info",
        lambda t: {"longName": f"{t} Inc", "currentPrice": 10.0, "targetMeanPrice": 12.0, "trailingPE": 20.0},
    )
    monkeypatch.setattr(market_data, "get_price_history", lambda t, p="1Y": [{"close": 9.0}] * 130)
    body = client.get("/stocks/abc/snapshot").json()
    assert body["profile"]["companyName"] == "ABC Inc"
    assert body["analysts"]["impliedUpsidePct"] == 20.0
    assert body["ratios"]["peRatio"] == 20.0
    assert body["price"]["change1MonthPct"] == pytest.approx(11.1)


def test_analysis_stream_endpoint(client, monkeypatch, fixture_text):
    install_fake_sources(monkeypatch, fixture_text)
    install_fake_llm(monkeypatch)
    with client.stream("GET", "/analysis/EXMP/stream") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        frames = [f for f in response.read().decode().split("\n\n") if f.startswith("event:")]
    names = [f.splitlines()[0].removeprefix("event: ") for f in frames]
    assert names[0] == "stage" and names[-1] == "report"
    report = json.loads(frames[-1].splitlines()[1].removeprefix("data: "))
    assert report["data"]["report"]["recommendation"] == "BUY"

    # history endpoints see the stored report
    listing = client.get("/reports/EXMP").json()
    assert len(listing) == 1 and listing[0]["recommendation"] == "BUY"
    stored = client.get(f"/reports/id/{listing[0]['id']}").json()
    assert stored["ticker"] == "EXMP"
    assert client.get("/reports/id/999999").status_code == 404


def test_track_record_scoring(client, monkeypatch, fixture_text):
    install_fake_sources(monkeypatch, fixture_text)
    install_fake_llm(monkeypatch)
    client.get("/analysis/EXMP")  # BUY at $100 with SPY at $500
    prices = {"EXMP": 115.0, "SPY": 520.0}  # +15% vs +4%
    monkeypatch.setattr(history, "_price_now", lambda t: prices[t])

    young = client.get("/reports/track-record").json()
    assert young["scoredReports"] == 0 and young["reports"][0]["matured"] is False

    body = client.get("/reports/track-record?min_age_days=0").json()
    row = body["reports"][0]
    assert row["returnPct"] == 15.0 and row["benchmarkReturnPct"] == 4.0 and row["excessReturnPct"] == 11.0
    assert row["hit"] is True and body["hitRate"] == 1.0


@pytest.mark.parametrize(
    ("rec", "excess", "hit"),
    [
        ("BUY", 3.0, True),
        ("BUY", -1.0, False),
        ("SELL", -2.0, True),
        ("SELL", 2.0, False),
        ("HOLD", 4.9, True),
        ("HOLD", -6.0, False),
    ],
)
def test_hit_rules(rec, excess, hit):
    assert history.score(rec, excess) is hit


def test_rag_endpoints_without_index(client):
    assert client.get("/rag/AAPL/documents").json()["documents"] == []
    assert client.get("/rag/AAPL/search", params={"q": "liquidity"}).json()["hits"] == []
    assert client.post("/rag/AAPL/ask", json={"question": "x"}).status_code == 422  # too short
