// Fictional company and numbers, for tests only.

export const analysisResponse = {
  ticker: 'ACME',
  companyName: 'Acme Robotics Inc.',
  analysisDate: '2026-10-27',
  generatedAt: '2026-10-27T14:03:11+00:00',
  report: {
    companyName: 'Acme Robotics Inc.',
    overallSignal: 'BULLISH',
    recommendation: 'BUY',
    confidenceScore: 72,
    summary: { text: 'Acme grew warehouse-robot revenue for a fifth straight quarter.', sources: ['F2', 'T1'] },
    valuation: { assessment: 'FAIRLY VALUED', reasoning: 'Trades near its peer median on forward earnings, at $250 apparently.', sources: ['M1', 'P1'] },
    financialHealth: { assessment: 'STRONG', reasoning: 'Net cash balance sheet.', sources: ['F4'] },
    strengths: [{ text: 'Recurring software attach rate is rising.', sources: ['F1'] }],
    risks: [{ text: 'Customer concentration in two retailers.', sources: ['F3', 'N2'] }],
    catalysts: [{ text: 'New mid-size robot ships next quarter.', sources: ['T2'] }],
    competitivePosition: { text: 'Leads on uptime.', sources: ['P1'] },
    managementTone: { text: 'Management sounded confident but cautious on margins.', sources: ['T1', 'T2'] },
    recentNewsImpact: { text: 'A large order was announced.', sources: ['N1'] },
    priceContext: { text: 'Shares are up 12% over three months.', sources: ['M2'] },
    analystConsensus: { text: 'Most analysts rate it a buy with a $999 target in prose.', sources: ['A1'] },
    recommendationReasoning: { text: 'Growth outweighs concentration risk.', sources: ['F2', 'A1'] },
  },
  sources: [
    { id: 'F1', kind: '10-K', label: 'ACME 10-K (FY2026) · Business', url: 'https://example.com/acme-10k', date: '2026-08-30', excerpt: 'Software subscriptions grew to 31% of revenue.' },
    { id: 'F2', kind: '10-K', label: 'ACME 10-K (FY2026) · MD&A', url: 'https://example.com/acme-10k#mda', date: '2026-08-30', excerpt: 'Revenue increased 18% year over year.' },
    { id: 'F3', kind: '10-K', label: 'ACME 10-K (FY2026) · Risk Factors', url: 'https://example.com/acme-10k#risk', date: '2026-08-30', excerpt: 'Two customers accounted for 41% of revenue.' },
    { id: 'F4', kind: '10-Q', label: 'ACME 10-Q (Q1 FY2027) · Balance sheet', url: null, date: '2026-10-05', excerpt: 'Cash and equivalents of $1.2 billion.' },
    { id: 'T1', kind: 'transcript', label: 'ACME Q1 FY2027 earnings call', url: null, date: '2026-10-06', excerpt: 'We remain confident in demand.' },
    { id: 'T2', kind: 'transcript', label: 'ACME Q1 FY2027 earnings call · Q&A', url: null, date: '2026-10-06', excerpt: 'The new model ships in the coming quarter.' },
    { id: 'M1', kind: 'market', label: 'Company profile & fundamentals', url: null, date: null, excerpt: 'Forward P/E 24.' },
    { id: 'M2', kind: 'market', label: 'Price momentum', url: null, date: null, excerpt: '3M change +12%.' },
    { id: 'A1', kind: 'analysts', label: 'Analyst consensus', url: null, date: null, excerpt: 'Mean target 132.50.' },
    { id: 'P1', kind: 'peers', label: 'Peer comparison', url: null, date: null, excerpt: 'Peer median forward P/E 23.' },
    { id: 'N1', kind: 'news', label: 'Acme wins large order (Example Wire)', url: 'https://example.com/news/1', date: '2026-10-20 13:00 UTC', excerpt: 'Acme announced an order.' },
    { id: 'N2', kind: 'news', label: 'Retail capex slows (Example Wire)', url: 'https://example.com/news/2', date: '2026-10-18 09:00 UTC', excerpt: 'Retailers trim budgets.' },
  ],
  metrics: { currentPrice: 120.0, targetMeanPrice: 132.5, impliedUpsidePct: 10.4, numberOfAnalysts: 14 },
  meta: {
    model: 'claude-opus-5-5',
    inputTokens: 31250,
    outputTokens: 2890,
    cacheReadTokens: 0,
    stopReason: 'end_turn',
    latencyMs: 41000,
    totalLatencyMs: 52000,
    cached: true,
    reportId: 17,
    benchmarkPrice: 500,
    sourceStatus: [
      { name: 'profile', label: 'Company profile', status: 'ok', ms: 410, detail: null },
      { name: 'transcript', label: 'Earnings call transcript', status: 'skipped', ms: 0, detail: 'EARNINGSCALL_API_KEY not set' },
      { name: 'insider', label: 'Insider trades', status: 'error', ms: 3001, detail: 'SEC request timed out' },
      { name: 'news', label: 'News (14 days)', status: 'empty', ms: 820, detail: null },
    ],
    retrieval: { mode: 'hybrid', embedder: 'voyage:voyage-finance-2', documents: ['ACME:doc-1', 'ACME:doc-2'], chunks: 18 },
    citations: { total: 44, invalidRemoved: 1, claims: 20, groundedClaims: 19, groundedness: 0.95 },
  },
}

export const snapshot = {
  profile: {
    symbol: 'ACME',
    companyName: 'Acme Robotics Inc.',
    sector: 'Industrials',
    industry: 'Robotics',
    description: 'Acme builds warehouse robots.',
    marketCap: 12_000_000_000,
    country: 'United States',
    employees: 4200,
    currentPrice: 120,
    currency: 'USD',
    exchange: 'NMS',
  },
  ratios: { peRatio: 30.1, forwardPE: 24, grossMargin: 0.46 },
  analysts: { targetMeanPrice: 132.5, impliedUpsidePct: 10.4, numberOfAnalysts: 14 },
  price: { currentPrice: 120, change1MonthPct: 3.2, change3MonthPct: 12, change6MonthPct: -4.1, priceVs200dmaPct: 6.5 },
}

export const askResponse = {
  ticker: 'ACME',
  question: 'How much did software revenue grow?',
  answer: [
    { text: 'Software subscriptions reached 31% of revenue', citations: [{ source: 0, citedText: 'Software subscriptions grew to 31% of revenue.' }] },
    { text: ', helped by higher attach rates', citations: [{ source: 1, citedText: 'Attach rates rose.' }, { source: 1, citedText: 'dup' }] },
    { text: '.', citations: [] },
  ],
  sources: [
    { index: 0, chunkId: 'c0', label: 'ACME 10-K (FY2026) · MD&A', url: 'https://example.com/acme-10k', date: '2026-08-30', score: 0.03, excerpt: 'Software subscriptions grew to 31% of revenue.' },
    { index: 1, chunkId: 'c1', label: 'ACME Q1 FY2027 earnings call', url: null, date: '2026-10-06', score: 0.02, excerpt: 'Attach rates rose across regions.' },
  ],
  documents: 5,
  meta: { model: 'claude-opus-5-5', inputTokens: 9000, outputTokens: 300, latencyMs: 6000 },
}

/** Shape of an axios error carrying the backend's JSON error body. */
export function apiError(status, detail, error = 'upstream_error') {
  const err = new Error(`Request failed with status code ${status}`)
  err.isAxiosError = true
  err.response = { status, data: { error, detail } }
  err.request = {}
  return err
}
