import { useState, useEffect, useCallback } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import { getHistory } from '../services/api'

const PERIODS = ['1W', '1M', '3M', '6M', '1Y', '2Y']

function formatDate(dateStr, period) {
  const d = new Date(dateStr)
  if (period === '1W') {
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  }
  if (period === '1M' || period === '3M') {
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

function formatPrice(n) {
  return n != null ? `$${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'
}

function formatVolume(n) {
  if (n == null) return '—'
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`
  return n
}

function CustomTooltip({ active, payload, period }) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload
  return (
    <div style={styles.tooltip}>
      <div style={styles.tooltipDate}>{formatDate(d.date, period)}</div>
      <div style={styles.tooltipRow}>
        <span style={styles.tooltipLabel}>CLOSE</span>
        <span style={styles.tooltipVal}>{formatPrice(d.close)}</span>
      </div>
      <div style={styles.tooltipRow}>
        <span style={styles.tooltipLabel}>OPEN</span>
        <span style={{ ...styles.tooltipVal, color: 'var(--text-secondary)' }}>{formatPrice(d.open)}</span>
      </div>
      <div style={styles.tooltipRow}>
        <span style={styles.tooltipLabel}>HIGH</span>
        <span style={{ ...styles.tooltipVal, color: 'var(--accent-green)' }}>{formatPrice(d.high)}</span>
      </div>
      <div style={styles.tooltipRow}>
        <span style={styles.tooltipLabel}>LOW</span>
        <span style={{ ...styles.tooltipVal, color: 'var(--accent-red)' }}>{formatPrice(d.low)}</span>
      </div>
      <div style={{ ...styles.tooltipRow, marginTop: '6px', paddingTop: '6px', borderTop: '1px solid var(--border)' }}>
        <span style={styles.tooltipLabel}>VOL</span>
        <span style={{ ...styles.tooltipVal, color: 'var(--text-muted)' }}>{formatVolume(d.volume)}</span>
      </div>
    </div>
  )
}

export default function PriceChart({ ticker, currentPrice }) {
  const [period, setPeriod] = useState('1Y')
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const fetchHistory = useCallback((p) => {
    setLoading(true)
    setError(false)
    getHistory(ticker, p)
      .then(res => {
        setData(res.data || [])
        setLoading(false)
      })
      .catch(() => {
        setError(true)
        setLoading(false)
      })
  }, [ticker])

  useEffect(() => {
    fetchHistory(period)
  }, [fetchHistory, period])

  // Derived stats
  const first = data[0]?.close
  const last = data[data.length - 1]?.close ?? currentPrice
  const change = first != null && last != null ? last - first : null
  const changePct = first != null && change != null ? (change / first) * 100 : null
  const isUp = change == null ? true : change >= 0

  const accentColor = isUp ? 'var(--accent-green)' : 'var(--accent-red)'
  const accentHex = isUp ? '#00ff88' : '#ff4d4d'

  // Tick count by period
  const tickCount = { '1W': 7, '1M': 6, '3M': 6, '6M': 6, '1Y': 6, '2Y': 5 }[period] || 6

  // X-axis tick label formatter
  const xTickFmt = (v) => {
    const d = new Date(v)
    if (period === '1W') return d.toLocaleDateString('en-US', { weekday: 'short' })
    if (period === '1M') return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    if (period === '3M') return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
  }

  return (
    <div style={styles.card}>
      {/* Header row */}
      <div style={styles.cardHeader}>
        <span style={styles.cardLabel}>PRICE CHART</span>
        <div style={styles.periodRow}>
          {PERIODS.map(p => (
            <button
              key={p}
              style={{ ...styles.periodBtn, ...(p === period ? styles.periodBtnActive : {}) }}
              onClick={() => setPeriod(p)}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Stats row */}
      <div style={styles.statsRow}>
        <span style={{ ...styles.currentPrice, color: accentColor }}>
          {formatPrice(last)}
        </span>
        {change != null && (
          <span style={{ ...styles.changeChip, background: isUp ? 'rgba(0,255,136,0.1)' : 'rgba(255,77,77,0.1)', color: accentColor }}>
            {isUp ? '▲' : '▼'} {formatPrice(Math.abs(change))} ({changePct >= 0 ? '+' : ''}{changePct?.toFixed(2)}%)
          </span>
        )}
        <span style={styles.periodLabel}>{period}</span>
      </div>

      {/* Chart area */}
      <div style={styles.chartWrap}>
        {loading && (
          <div style={styles.overlay}>
            <div style={styles.miniSpinner} />
          </div>
        )}
        {error && !loading && (
          <div style={styles.overlay}>
            <span style={styles.errorMsg}>FAILED TO LOAD CHART DATA</span>
          </div>
        )}
        {!loading && !error && data.length > 0 && (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`chartGrad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={accentHex} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={accentHex} stopOpacity={0} />
                </linearGradient>
              </defs>

              <XAxis
                dataKey="date"
                tickFormatter={xTickFmt}
                tickCount={tickCount}
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)', letterSpacing: 0.5 }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={['auto', 'auto']}
                tickFormatter={v => `$${v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v}`}
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                axisLine={false}
                tickLine={false}
                width={52}
                orientation="right"
              />
              <Tooltip
                content={<CustomTooltip period={period} />}
                cursor={{ stroke: 'var(--border-bright)', strokeWidth: 1, strokeDasharray: '4 4' }}
              />
              {/* Entry price reference line */}
              {first != null && (
                <ReferenceLine
                  y={first}
                  stroke="var(--border-bright)"
                  strokeDasharray="3 3"
                  strokeWidth={1}
                />
              )}
              <Area
                type="monotone"
                dataKey="close"
                stroke={accentHex}
                strokeWidth={1.5}
                fill={`url(#chartGrad-${ticker})`}
                dot={false}
                activeDot={{ r: 3, fill: accentHex, stroke: 'var(--bg-primary)', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 52-week range bar */}
      {!loading && data.length > 0 && (() => {
        const closes = data.map(d => d.close)
        const lo = Math.min(...closes)
        const hi = Math.max(...closes)
        const pct = hi > lo ? ((last - lo) / (hi - lo)) * 100 : 50
        return (
          <div style={styles.rangeWrap}>
            <span style={styles.rangeLabel}>{formatPrice(lo)}</span>
            <div style={styles.rangeBar}>
              <div style={{ ...styles.rangeBarFill, width: `${pct}%`, background: accentColor }} />
              <div style={{ ...styles.rangeThumb, left: `calc(${pct}% - 3px)`, background: accentColor }} />
            </div>
            <span style={styles.rangeLabel}>{formatPrice(hi)}</span>
          </div>
        )
      })()}
    </div>
  )
}

const styles = {
  card: {
    background: 'var(--bg-card)',
    padding: '24px 24px 20px',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '14px',
  },
  cardLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '4px',
    color: 'var(--text-muted)',
  },
  periodRow: {
    display: 'flex',
    gap: '2px',
  },
  periodBtn: {
    background: 'transparent',
    border: '1px solid transparent',
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '1px',
    padding: '4px 8px',
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  periodBtnActive: {
    border: '1px solid var(--border-bright)',
    color: 'var(--accent-green)',
  },
  statsRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '12px',
    marginBottom: '16px',
  },
  currentPrice: {
    fontFamily: 'var(--font-mono)',
    fontSize: '28px',
    fontWeight: 700,
    letterSpacing: '1px',
  },
  changeChip: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    padding: '3px 8px',
    borderRadius: '2px',
    fontWeight: 600,
  },
  periodLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
    marginLeft: 'auto',
  },
  chartWrap: {
    position: 'relative',
    height: '220px',
  },
  overlay: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  miniSpinner: {
    width: '24px',
    height: '24px',
    border: '2px solid var(--border)',
    borderTop: '2px solid var(--accent-green)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  errorMsg: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--accent-red)',
    letterSpacing: '2px',
  },
  // 52w range bar
  rangeWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginTop: '16px',
    paddingTop: '14px',
    borderTop: '1px solid var(--border)',
  },
  rangeLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
    whiteSpace: 'nowrap',
  },
  rangeBar: {
    flex: 1,
    height: '4px',
    background: 'var(--border)',
    borderRadius: '2px',
    position: 'relative',
  },
  rangeBarFill: {
    height: '100%',
    borderRadius: '2px',
    opacity: 0.4,
  },
  rangeThumb: {
    position: 'absolute',
    top: '-2px',
    width: '6px',
    height: '8px',
    borderRadius: '1px',
  },
  // Tooltip
  tooltip: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-bright)',
    padding: '10px 14px',
    fontFamily: 'var(--font-mono)',
  },
  tooltipDate: {
    fontSize: '9px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
    marginBottom: '8px',
  },
  tooltipRow: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '20px',
    marginBottom: '3px',
  },
  tooltipLabel: {
    fontSize: '9px',
    color: 'var(--text-muted)',
    letterSpacing: '1px',
  },
  tooltipVal: {
    fontSize: '11px',
    color: 'var(--text-primary)',
    fontWeight: 700,
  },
}
