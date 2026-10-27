import axios from 'axios'

/** Base URL of the FastAPI backend, without a trailing slash. */
export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '')

const api = axios.create({ baseURL: API_URL, timeout: 60_000 })

// Retrieval endpoints may fetch and embed filings on first use, and the
// blocking analysis endpoint can take up to two minutes.
const SLOW = 180_000

const enc = encodeURIComponent
const unwrap = (request) => request.then((res) => res.data)

// ── Market data ─────────────────────────────────────────────────────────────
export const getSnapshot = (ticker, { signal } = {}) =>
  unwrap(api.get(`/stocks/${enc(ticker)}/snapshot`, { signal }))

export const getProfile = (ticker, { signal } = {}) =>
  unwrap(api.get(`/stocks/${enc(ticker)}/profile`, { signal }))

export const getRatios = (ticker, { signal } = {}) =>
  unwrap(api.get(`/stocks/${enc(ticker)}/ratios`, { signal }))

export const getCompetitors = (ticker, { signal } = {}) =>
  unwrap(api.get(`/stocks/${enc(ticker)}/competitors`, { signal }))

export const getHistory = (ticker, period = '1Y', { signal } = {}) =>
  unwrap(api.get(`/stocks/${enc(ticker)}/history`, { params: { period }, signal }))

// ── AI analysis ─────────────────────────────────────────────────────────────
/** Blocking variant; prefer the SSE stream (see `analysisStreamUrl`). */
export const getAnalysis = (ticker, { refresh = false, signal } = {}) =>
  unwrap(api.get(`/analysis/${enc(ticker)}`, { params: { refresh }, signal, timeout: SLOW }))

/** URL for `new EventSource(...)`: emits `stage`, `source`, then `report` or `error`. */
export const analysisStreamUrl = (ticker, { refresh = false } = {}) =>
  `${API_URL}/analysis/${enc(ticker)}/stream?refresh=${refresh ? 'true' : 'false'}`

// ── Retrieval over filings & earnings calls ────────────────────────────────
export const getRagDocuments = (ticker, { signal } = {}) =>
  unwrap(api.get(`/rag/${enc(ticker)}/documents`, { signal }))

export const indexFilings = (ticker, { signal } = {}) =>
  unwrap(api.post(`/rag/${enc(ticker)}/index`, null, { signal, timeout: SLOW }))

export const searchFilings = (ticker, q, { k = 8, signal } = {}) =>
  unwrap(api.get(`/rag/${enc(ticker)}/search`, { params: { q, k }, signal }))

export const askFilings = (ticker, question, { signal } = {}) =>
  unwrap(api.post(`/rag/${enc(ticker)}/ask`, { question }, { signal, timeout: SLOW }))

export const getRiskDiff = (ticker, { signal } = {}) =>
  unwrap(api.get(`/rag/${enc(ticker)}/risk-diff`, { signal, timeout: SLOW }))

// ── Report history & track record ──────────────────────────────────────────
export const getReports = (ticker, { limit = 20, signal } = {}) =>
  unwrap(api.get(`/reports/${enc(ticker)}`, { params: { limit }, signal }))

export const getReportById = (id, { signal } = {}) =>
  unwrap(api.get(`/reports/id/${enc(id)}`, { signal }))

export const getTrackRecord = ({ minAgeDays = 7, signal } = {}) =>
  unwrap(api.get('/reports/track-record', { params: { min_age_days: minAgeDays }, signal }))

export const getHealth = ({ signal } = {}) => unwrap(api.get('/health', { signal }))

// ── Errors ──────────────────────────────────────────────────────────────────
/** True when the request was cancelled through an AbortController. */
export const isAbortError = (error) =>
  axios.isCancel(error) || error?.name === 'AbortError' || error?.name === 'CanceledError'

/**
 * Human-readable message for a failed request.
 *
 * The backend answers every failure with `{error, detail, source?}`; FastAPI's own
 * request validation answers `{detail: [{msg, loc}, ...]}`. Network failures and
 * timeouts have no response body at all.
 */
export function getErrorDetail(error, fallback = 'Something went wrong. Please try again.') {
  if (!error) return fallback
  if (isAbortError(error)) return 'Request cancelled.'

  const body = error.response?.data
  if (body && typeof body === 'object') {
    const { detail } = body
    if (typeof detail === 'string' && detail.trim()) return detail
    if (Array.isArray(detail) && detail.length) {
      return detail.map((d) => (typeof d === 'string' ? d : d?.msg)).filter(Boolean).join('; ') || fallback
    }
    if (typeof body.error === 'string') return body.error.replace(/_/g, ' ')
  }
  if (typeof body === 'string' && body.trim() && !body.trim().startsWith('<')) return body.trim()

  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return 'The request timed out. The data provider may be slow; please retry.'
  }
  if (error.response?.status) return `Request failed with status ${error.response.status}.`
  if (error.request || error.code === 'ERR_NETWORK') {
    return `Cannot reach the API at ${API_URL}. Is the backend running?`
  }
  return error.message || fallback
}
