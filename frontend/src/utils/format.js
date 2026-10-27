const isNum = (n) => n != null && Number.isFinite(Number(n))

export const DASH = '—'

export function formatPrice(n, currency = 'USD') {
  if (!isNum(n)) return DASH
  const symbol = currency === 'USD' || !currency ? '$' : ''
  const value = Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return symbol ? `${symbol}${value}` : `${value} ${currency}`
}

export function formatNumber(n, decimals = 2) {
  return isNum(n) ? Number(n).toFixed(decimals) : DASH
}

export function formatInteger(n) {
  return isNum(n) ? Math.round(Number(n)).toLocaleString('en-US') : DASH
}

/** 0.463 → "46.3%" (backend ratios are fractions). */
export function formatFraction(n, decimals = 1) {
  return isNum(n) ? `${(Number(n) * 100).toFixed(decimals)}%` : DASH
}

/** 8.1 → "+8.1%" (values that are already percentages). */
export function formatSignedPct(n, decimals = 1) {
  if (!isNum(n)) return DASH
  const v = Number(n)
  return `${v > 0 ? '+' : ''}${v.toFixed(decimals)}%`
}

/** 2.9e12 → "$2.90T" */
export function formatMoneyCompact(n) {
  if (!isNum(n)) return DASH
  const v = Number(n)
  const abs = Math.abs(v)
  if (abs >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
  if (abs >= 1e9) return `$${(v / 1e9).toFixed(1)}B`
  if (abs >= 1e6) return `$${(v / 1e6).toFixed(1)}M`
  return `$${v.toLocaleString('en-US')}`
}

export function formatCompact(n) {
  if (!isNum(n)) return DASH
  return Number(n).toLocaleString('en-US', { notation: 'compact', maximumFractionDigits: 1 })
}

export function formatMs(ms) {
  if (!isNum(ms)) return DASH
  const v = Number(ms)
  return v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${Math.round(v)}ms`
}

/** Accepts unix seconds, ms, or an ISO string. */
export function toDate(value) {
  if (value == null || value === '') return null
  if (typeof value === 'number') return new Date(value < 1e12 ? value * 1000 : value)
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

export function formatDate(value) {
  const d = toDate(value)
  return d ? d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : DASH
}

export function formatDateTime(value) {
  const d = toDate(value)
  return d
    ? d.toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : DASH
}

export const toneColor = (n) =>
  !isNum(n) ? 'var(--text-secondary)' : Number(n) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'

export const signalColor = (s) =>
  ({ BULLISH: 'var(--accent-green)', BEARISH: 'var(--accent-red)', NEUTRAL: 'var(--accent-yellow)' })[s] ||
  'var(--text-secondary)'

export const recColor = (r) =>
  ({ BUY: 'var(--accent-green)', SELL: 'var(--accent-red)', HOLD: 'var(--accent-yellow)' })[r] ||
  'var(--text-secondary)'
