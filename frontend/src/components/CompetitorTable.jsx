import { Link } from 'react-router-dom'
import { formatFraction as pct, formatMoneyCompact as fmtB, formatNumber } from '../utils/format'
import { getErrorDetail } from '../services/api'
import ErrorNotice from './ErrorNotice'

const fmt = (n) => formatNumber(n, 1)

export default function CompetitorTable({ competitors, ticker, loading, error, onRetry }) {
  if (loading || error) {
    return (
      <section className="panel" aria-label="Competitor comparison">
        <div className="panel-title">COMPETITOR COMPARISON</div>
        {loading ? (
          <p style={styles.muted}>Loading peer metrics…</p>
        ) : (
          <ErrorNotice title="PEERS UNAVAILABLE" detail={getErrorDetail(error)} onRetry={onRetry} compact />
        )}
      </section>
    )
  }
  if (!competitors) return null
  const entries = Object.entries(competitors)

  return (
    <section className="panel" aria-label="Competitor comparison">
      <div className="panel-title">COMPETITOR COMPARISON</div>
      <div className="table-wrap">
        <table style={styles.table}>
          <thead>
            <tr>
              {['TICKER', 'MKT CAP', 'P/E', 'P/B', 'EV/EBITDA', 'GROSS MARGIN', 'ROE', 'D/E'].map(h => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {entries.map(([t, d]) => (
              <tr key={t} style={t === ticker ? styles.activeRow : styles.row}>
                <td style={{ ...styles.td, ...styles.tickerCell }}>
                  {t === ticker ? t : <Link to={`/stock/${t}`} title={d.name}>{t}</Link>}
                </td>
                <td style={styles.td}>{fmtB(d.marketCap)}</td>
                <td style={styles.td}>{fmt(d.peRatio)}</td>
                <td style={styles.td}>{fmt(d.pbRatio)}</td>
                <td style={styles.td}>{fmt(d.evToEbitda)}</td>
                <td style={styles.td}>{pct(d.grossMargin)}</td>
                <td style={styles.td}>{pct(d.returnOnEquity)}</td>
                <td style={styles.td}>{fmt(d.debtToEquity)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

const styles = {
  muted: { fontSize: '12px', color: 'var(--text-muted)' },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontFamily: 'var(--font-mono)',
  },
  th: {
    fontSize: '9px',
    letterSpacing: '2px',
    color: 'var(--text-muted)',
    padding: '8px 12px',
    textAlign: 'left',
    borderBottom: '1px solid var(--border)',
    whiteSpace: 'nowrap',
  },
  row: {
    borderBottom: '1px solid var(--border)',
  },
  activeRow: {
    borderBottom: '1px solid var(--border)',
    background: 'rgba(0, 255, 136, 0.05)',
  },
  td: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    padding: '10px 12px',
    whiteSpace: 'nowrap',
  },
  tickerCell: {
    color: 'var(--accent-green)',
    fontWeight: 700,
    letterSpacing: '2px',
  },
}