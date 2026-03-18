import { useMemo } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'

function computeMA(data, window) {
  return data.map((_, i) => {
    if (i < window - 1) return null
    const slice = data.slice(i - window + 1, i + 1)
    return Math.round((slice.reduce((s, d) => s + d.close, 0) / window) * 100) / 100
  })
}

function formatMonth(dateStr) {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const d = new Date(dateStr)
  return months[d.getMonth()]
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={styles.tooltip}>
      <div style={styles.tooltipDate}>{label}</div>
      <div style={styles.tooltipPrice}>${payload[0].value.toFixed(2)}</div>
    </div>
  )
}

export default function PriceChart({ history, ticker }) {
  const { chartData, ma50, ma200 } = useMemo(() => {
    if (!history || !history.length) return { chartData: [], ma50: null, ma200: null }

    const ma50Arr = computeMA(history, 50)
    const ma200Arr = computeMA(history, 200)

    const validMA50 = ma50Arr.filter((v) => v !== null)
    const validMA200 = ma200Arr.filter((v) => v !== null)

    return {
      chartData: history.map((d) => ({ date: d.date, close: d.close })),
      ma50: validMA50.length ? validMA50[validMA50.length - 1] : null,
      ma200: validMA200.length ? validMA200[validMA200.length - 1] : null,
    }
  }, [history])

  if (!chartData.length) return null

  const seenMonths = new Set()
  const tickFormatter = (dateStr) => {
    const m = formatMonth(dateStr)
    if (seenMonths.has(m)) return ''
    seenMonths.add(m)
    return m
  }

  return (
    <div style={styles.card}>
      <div style={styles.header}>PRICE — 6M</div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={`priceGrad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent-green)" stopOpacity={0.18} />
              <stop offset="100%" stopColor="var(--accent-green)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border)"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tickFormatter={tickFormatter}
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-muted)' }}
            axisLine={{ stroke: 'var(--border)' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            orientation="right"
            domain={['auto', 'auto']}
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-muted)' }}
            axisLine={{ stroke: 'var(--border)' }}
            tickLine={false}
            tickFormatter={(v) => v.toFixed(0)}
            width={48}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="close"
            stroke="var(--accent-green)"
            strokeWidth={1.5}
            fill={`url(#priceGrad-${ticker})`}
            dot={false}
            activeDot={{ r: 3, stroke: 'var(--accent-green)', strokeWidth: 1, fill: 'var(--bg-card)' }}
          />
          {ma50 !== null && (
            <ReferenceLine
              y={ma50}
              stroke="var(--accent-blue)"
              strokeDasharray="4 3"
              strokeWidth={1}
              label={{
                value: '50D',
                position: 'insideTopRight',
                fill: 'var(--accent-blue)',
                fontSize: 9,
                fontFamily: 'var(--font-mono)',
              }}
            />
          )}
          {ma200 !== null && (
            <ReferenceLine
              y={ma200}
              stroke="var(--accent-yellow)"
              strokeDasharray="4 3"
              strokeWidth={1}
              label={{
                value: '200D',
                position: 'insideBottomRight',
                fill: 'var(--accent-yellow)',
                fontSize: 9,
                fontFamily: 'var(--font-mono)',
              }}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

const styles = {
  card: {
    background: 'var(--bg-card)',
    padding: '28px',
  },
  header: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '4px',
    color: 'var(--text-muted)',
    marginBottom: '16px',
  },
  tooltip: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border-bright)',
    padding: '8px 12px',
  },
  tooltipDate: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
    marginBottom: '4px',
  },
  tooltipPrice: {
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    color: 'var(--text-primary)',
    fontWeight: 700,
  },
}
