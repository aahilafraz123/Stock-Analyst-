<div align="center">

# 📈 StockAnalyzer

### AI-Powered Equity Research Terminal

**Type a ticker. Get an institutional-grade investment report in seconds.**

StockAnalyzer fans out across **10 live financial data sources** — SEC filings, earnings call transcripts, insider trades, institutional ownership, analyst consensus, real-time news, and price momentum — assembles them into a single rich context, and hands it to **Claude** to produce a structured, opinionated equity research report.

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-7-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-D97757?style=for-the-badge&logo=anthropic&logoColor=white)

</div>

---

## 🎯 What it does

Most stock screeners show you numbers. StockAnalyzer reads the homework a human analyst would read — the **10-Q**, the **10-K risk factors**, the **earnings call transcript**, what **insiders** and **institutions** are doing, what **Wall Street** thinks, and the **last two weeks of news** — and synthesizes it all into a single verdict:

> **Signal · Recommendation · Confidence · Valuation · Strengths · Risks · Competitive Position**

The key idea: an LLM is only as good as its context. Instead of asking Claude "what do you think of AAPL?" from memory, the backend **does the research first** — pulling and parsing primary-source documents in parallel — then asks Claude to reason over real, current data.

---

## ✨ Highlights

- **🔀 10 data sources, fetched in parallel.** A single analysis request triggers 12 concurrent fetches via `asyncio.gather` + thread executors. Slow, blocking SEC/yfinance calls run alongside async HTTP news fetches — wall-clock time is the slowest single source, not the sum.
- **📄 Real SEC filing parsing.** Downloads the latest **10-Q** and **10-K** straight from SEC EDGAR, prefers the PDF rendering (via `pdfplumber`), and falls back to HTML. A custom section extractor pulls **MD&A, Results of Operations, Liquidity, and Risk Factors** — using a longest-match heuristic to skip table-of-contents noise.
- **🎙️ Earnings call transcripts.** Fetches the most recent call and **splits prepared remarks from the analyst Q&A** so Claude can weigh management's narrative against the hard questions.
- **🏛️ Insider & institutional flow.** Surfaces recent insider buys/sells and the largest institutional holders — including who's **increasing vs. decreasing** their position.
- **🧠 Structured AI output.** Claude is constrained to a strict JSON schema, so every report is consistent and directly renderable — no prose parsing.
- **🖥️ Bloomberg-terminal aesthetic.** A dark, monospace, grid-lined React UI that loads fast fundamentals immediately and streams in the heavier AI report independently.
- **🛡️ Fault-tolerant by design.** Any single source can fail (rate limit, missing filing, no transcript) and the analysis still completes — failures are caught per-source and passed to Claude as "Not available."

---

## 🏗️ Architecture

```
                          ┌─────────────────────────────────┐
                          │   React + Vite Frontend (5173)   │
                          │  Search → Terminal Dashboard     │
                          └───────────────┬─────────────────┘
                                          │  axios
                          ┌───────────────▼─────────────────┐
                          │      FastAPI Backend (8000)      │
                          │   /stocks /news /filings /analysis │
                          └───────────────┬─────────────────┘
                                          │ asyncio.gather (12 parallel tasks)
        ┌──────────────┬──────────────┬───┴────────┬──────────────┬──────────────┐
        ▼              ▼              ▼            ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ yfinance│   │SEC EDGAR │   │ Finnhub │  │earnings  │  │ insider  │  │ instit.  │
   │ profile │   │10-Q/10-K │   │ news +  │  │ call     │  │ trades   │  │ holders  │
   │ ratios  │   │ PDF/HTML │   │sentiment│  │transcript│  │(yfinance)│  │(yfinance)│
   │ price   │   │ parser   │   │         │  │          │  │          │  │          │
   │ analysts│   └──────────┘   └─────────┘  └──────────┘  └──────────┘  └──────────┘
   │ peers   │
   └─────────┘
        │              │              │            │              │              │
        └──────────────┴──────────────┴─────┬──────┴──────────────┴──────────────┘
                                            ▼
                              ┌──────────────────────────┐
                              │   Context Assembler       │
                              │  (ai_service.py)          │
                              │  ~80k chars of evidence   │
                              └────────────┬─────────────┘
                                           ▼
                              ┌──────────────────────────┐
                              │   Claude (Sonnet 4.6)     │
                              │   → strict JSON report    │
                              └──────────────────────────┘
```

### The pipeline in one function

`ai_service.build_full_context()` is the heart of the system — it launches all 12 fetches at once and gracefully degrades on any failure:

```python
results = await asyncio.gather(
    profile_task, ratios_task, competitors_task, price_task, analyst_task,
    filing_10q_task, filing_10k_task, transcript_task, insider_task,
    institutional_task, news_task, sentiment_task,
    return_exceptions=True,   # one source failing never kills the analysis
)
```

The assembled evidence (capped per-source to fit Claude's context — 20k chars of 10-Q, 15k of 10-K, 10k of prepared remarks, etc.) is formatted into a single prompt, and Claude returns a structured report against a fixed schema.

---

## 📊 Data Sources

| Source | Provider | What it contributes |
|--------|----------|---------------------|
| Company profile | yfinance | Sector, industry, market cap, business summary |
| Financial ratios | yfinance | P/E, P/B, ROE, margins, debt/equity, EV/EBITDA, growth |
| Price & momentum | yfinance | 52-week range position, 50/200-DMA, 1M/3M change |
| Analyst consensus | yfinance | Mean/high/low price targets, implied upside, # of analysts |
| Peer comparison | yfinance | Side-by-side ratios vs. curated sector competitors |
| **10-Q filing** | SEC EDGAR | MD&A, Results of Operations, Liquidity, Risk Factors |
| **10-K annual report** | SEC EDGAR | Business overview, full-year risk factors, annual MD&A |
| **Earnings transcript** | earningscall | Prepared remarks + analyst Q&A, split apart |
| **Insider trades** | yfinance | Recent buys/sells, 6-month net activity |
| **Institutional ownership** | yfinance | Top holders, % held, increasing/decreasing positions |
| Company news (14d) | Finnhub + newspaper3k | Full article bodies, not just headlines |
| News sentiment | Finnhub | Buzz, bullish %, sector-relative scoring |

---

## 🧱 Tech Stack

**Backend** — Python · FastAPI · Uvicorn · `asyncio` · Anthropic SDK · yfinance · BeautifulSoup + lxml · pdfplumber · newspaper3k · httpx

**Frontend** — React 19 · Vite 7 · React Router 7 · Recharts · Axios · Space Mono / Syne typography

**AI** — Claude Sonnet 4.6 (`claude-sonnet-4-6`) with strict JSON-schema output

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/) and a free [Finnhub API key](https://finnhub.io/)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...
FINNHUB_API_KEY=your_finnhub_key
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

API docs are auto-generated at **http://localhost:8000/docs**.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**, type a ticker (e.g. `AAPL`), and hit **Analyze**.

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analysis/{ticker}` | **Full AI research report** (runs the entire pipeline) |
| `GET` | `/stocks/{ticker}/profile` | Company profile |
| `GET` | `/stocks/{ticker}/ratios` | Financial ratios |
| `GET` | `/stocks/{ticker}/competitors` | Peer comparison table |
| `GET` | `/stocks/{ticker}/history?period=1Y` | OHLCV price history |
| `GET` | `/news/{ticker}?days_back=7` | Recent news with full article text |
| `GET` | `/news/{ticker}/sentiment` | News sentiment scores |
| `GET` | `/filings/{ticker}` | Recent 10-Q filing metadata |
| `GET` | `/filings/{ticker}/text` | Parsed 10-Q key sections |

<details>
<summary><b>Example: AI analysis response shape</b></summary>

```json
{
  "ticker": "AAPL",
  "companyName": "Apple Inc.",
  "overallSignal": "BULLISH",
  "confidenceScore": 78,
  "summary": "...",
  "valuation": { "assessment": "FAIRLY VALUED", "reasoning": "..." },
  "strengths": ["...", "...", "..."],
  "risks": ["...", "...", "..."],
  "competitivePosition": "...",
  "recentNewsImpact": "...",
  "financialHealth": { "assessment": "STRONG", "reasoning": "..." },
  "priceContext": "...",
  "analystConsensus": "...",
  "recommendation": "BUY",
  "recommendationReasoning": "..."
}
```
</details>

---

## 📁 Project Structure

```
Stock-Analyst-/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app + CORS + routers
│   │   ├── routers/                # stocks, news, filings, analysis
│   │   └── services/
│   │       ├── ai_service.py       # ⭐ parallel fetch + Claude orchestration
│   │       ├── fmp_service.py      # yfinance: profile, ratios, price, analysts, peers
│   │       ├── edgar_service.py    # SEC 10-Q/10-K download + section parser
│   │       ├── news_service.py     # Finnhub news + full-text + sentiment
│   │       ├── transcript_service.py   # earnings call transcripts
│   │       ├── insider_service.py      # insider trades
│   │       └── institutional_service.py # institutional holders
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/        # SearchPage, StockPage
        ├── components/   # OverviewCard, RatiosPanel, PriceChart,
        │                 # CompetitorTable, AnalysisReport, Loader
        └── services/api.js
```

---

## 🧭 How a request flows

1. **User** searches a ticker → `StockPage` fires two parallel loads.
2. **Fast lane** (`/stocks/...`) returns profile, ratios, and peers immediately so the dashboard paints instantly.
3. **Slow lane** (`/analysis/...`) runs the full 12-source pipeline — SEC downloads, transcript fetch, news scraping — while a "Running AI Analysis" state shows.
4. **Claude** receives ~80k characters of fresh, structured evidence and returns the JSON verdict.
5. The **AnalysisReport** component renders signal, recommendation, confidence, valuation, strengths, and risks — color-coded BULLISH/BEARISH/NEUTRAL.

---

## 🗺️ Roadmap

- [ ] Streaming AI responses (token-by-token) instead of wait-then-render
- [ ] Response caching / persistence layer to avoid re-fetching within a session
- [ ] Watchlists and multi-ticker comparison view
- [ ] Dynamic peer discovery (replace the hardcoded peer map)
- [ ] Backtesting recommendations against subsequent price action
- [ ] Dockerized one-command deploy

---

## ⚠️ Disclaimer

StockAnalyzer is a **research and educational tool**. Its output is AI-generated and may contain errors or omissions. **Nothing here is financial advice.** Always do your own due diligence and consult a licensed professional before making investment decisions.

---

<div align="center">

**Built with FastAPI, React, and Claude.**

*Reads the filings so you don't have to.*

</div>
