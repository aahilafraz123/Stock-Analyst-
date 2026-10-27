/**
 * State machine for `/analysis/{ticker}/stream` (Server-Sent Events).
 *
 * phase: connecting → running → done | error
 * The reducer is pure so the progress logic can be tested without a network.
 */

/** The 13 sources the backend gathers, in display order (labels mirror the backend). */
export const SOURCES = [
  { name: 'profile', label: 'Company profile' },
  { name: 'ratios', label: 'Financial ratios' },
  { name: 'price', label: 'Price momentum' },
  { name: 'analysts', label: 'Analyst consensus' },
  { name: 'peers', label: 'Peer comparison' },
  { name: 'filing_10k', label: '10-K annual report' },
  { name: 'filing_10q', label: '10-Q quarterly report' },
  { name: 'transcript', label: 'Earnings call transcript' },
  { name: 'insider', label: 'Insider trades' },
  { name: 'institutional', label: 'Institutional ownership' },
  { name: 'news', label: 'News (14 days)' },
  { name: 'sentiment', label: 'News sentiment' },
  { name: 'benchmark', label: 'S&P 500 benchmark' },
]

/** Pipeline stages after the sources are gathered (`cached` short-circuits all of them). */
export const STAGES = [
  { id: 'sources', label: 'Gather' },
  { id: 'indexing', label: 'Index' },
  { id: 'retrieval', label: 'Retrieve' },
  { id: 'llm', label: 'Write' },
]

export const SOURCE_STATUSES = ['pending', 'ok', 'empty', 'error', 'skipped']
const FINAL = new Set(['ok', 'empty', 'error', 'skipped'])
const LLM_PHASES = ['thinking', 'writing']

export function createInitialState({ runId = 0, refresh = false } = {}) {
  return {
    runId,
    refresh,
    phase: 'connecting',
    stage: null,
    message: 'Connecting to the analysis stream',
    order: SOURCES.map((s) => s.name),
    sources: Object.fromEntries(
      SOURCES.map((s) => [s.name, { ...s, status: 'pending', ms: null, detail: null }]),
    ),
    llm: null, // { phase: 'thinking' | 'writing', chars } during the `llm` stage
    response: null,
    error: null,
  }
}

const isFinished = (state) => state.phase === 'done' || state.phase === 'error'

function applySource(state, event) {
  const { name } = event
  if (!name) return state
  const previous = state.sources[name]
  const status = SOURCE_STATUSES.includes(event.status) ? event.status : 'error'
  // Each source is announced as `pending` and then settles once; never regress.
  if (previous && FINAL.has(previous.status) && status === 'pending') return state

  const next = {
    name,
    label: event.label || previous?.label || name,
    status,
    ms: event.ms ?? previous?.ms ?? null,
    detail: event.detail ?? null,
  }
  return {
    ...state,
    phase: 'running',
    order: previous ? state.order : [...state.order, name],
    sources: { ...state.sources, [name]: next },
  }
}

export function analysisStreamReducer(state, action) {
  switch (action.type) {
    case 'restart':
      return createInitialState({ runId: state.runId + 1, refresh: Boolean(action.refresh) })

    case 'stage':
      if (isFinished(state)) return state
      return {
        ...state,
        phase: 'running',
        stage: action.payload.stage ?? state.stage,
        message: action.payload.message || state.message,
      }

    case 'source':
      if (isFinished(state)) return state
      return applySource(state, action.payload)

    case 'llm': {
      const { phase, chars } = action.payload || {}
      if (isFinished(state) || !LLM_PHASES.includes(phase)) return state
      return {
        ...state,
        phase: 'running',
        llm: { phase, chars: typeof chars === 'number' ? chars : (state.llm?.chars ?? null) },
      }
    }

    case 'report':
      return { ...state, phase: 'done', response: action.payload.data ?? null, error: null }

    case 'error': {
      const p = action.payload || {}
      return {
        ...state,
        phase: 'error',
        error: {
          status: p.status ?? null,
          code: p.error || 'error',
          detail: p.detail || 'The analysis failed.',
          source: p.source || null,
        },
      }
    }

    case 'connection_lost':
      // The browser fires a generic error when the stream closes; only a failure
      // if neither a report nor a server error arrived first.
      if (isFinished(state)) return state
      return {
        ...state,
        phase: 'error',
        error: { status: null, code: 'connection_lost', detail: action.detail, source: null },
      }

    default:
      return state
  }
}

/** 1234 → "1.2k" */
const formatChars = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k` : String(n))

/** The line shown under the stage bar: Claude's progress while writing, else the stage message. */
export function progressMessage(state) {
  if (state.stage === 'llm' && state.llm) {
    if (state.llm.phase === 'thinking') return 'Claude is reasoning over the evidence…'
    return state.llm.chars != null ? `Writing report · ${formatChars(state.llm.chars)} chars` : 'Writing report…'
  }
  return state.message
}

/** Sources in display order. */
export const sourceList = (state) => state.order.map((name) => state.sources[name])

/** Counts per status plus how many have settled. */
export function summarizeSources(state) {
  const counts = { total: 0, settled: 0, pending: 0, ok: 0, empty: 0, error: 0, skipped: 0 }
  for (const source of sourceList(state)) {
    counts.total += 1
    counts[source.status] += 1
    if (FINAL.has(source.status)) counts.settled += 1
  }
  return counts
}
