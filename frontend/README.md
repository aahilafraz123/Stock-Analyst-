# StockAnalyzer frontend

React 19 + Vite 7 terminal UI for the StockAnalyzer API (see `../backend`).

## Setup

```bash
cp .env.example .env        # VITE_API_URL, defaults to http://localhost:8000
npm install
npm run dev                 # http://localhost:5173
```

## Scripts

| Command         | What it does                                  |
| --------------- | --------------------------------------------- |
| `npm run dev`   | Vite dev server                               |
| `npm run build` | Production build into `dist/`                 |
| `npm run lint`  | ESLint (incl. `react-hooks` compiler rules)   |
| `npm test`      | Vitest + Testing Library (jsdom)              |

## Structure

- `src/services/api.js`: every backend endpoint, the SSE URL builder and `getErrorDetail`
- `src/hooks/useRequest.js`: keyed, abortable data fetching (loading/error are derived, never stale)
- `src/hooks/useAnalysisStream.js` + `src/state/analysisStream.js`: EventSource lifecycle and the pure reducer behind the live source-progress panel
- `src/pages/`: search, stock (`/stock/:ticker`) and track record (`/track-record`)
- `src/components/`: report with citation popovers, Ask-the-filings, risk-factor diff, report history, market data cards

For research and educational purposes only. Not investment advice.
