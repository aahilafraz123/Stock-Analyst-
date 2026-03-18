const fmt = (n, d = 1) => n != null ? Number(n).toFixed(d) : '—'
const pct = (n) => n != null ? `${(n * 100).toFixed(1)}%` : '—'
const fmtB = (n) => n != null ? `$${(n / 1e9).toFixed(0)}B` : '—'

export default function CompetitorTable({ competitors, ticker }) {
  if (!competitors) return null
  const entries = Object.entries(competitors)

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>COMPETITOR COMPARISON</div>
      <div style={styles.tableWrap}>
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
                <td style={{ ...styles.td, ...styles.tickerCell }}>{t}</td>
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
    </div>
  )
}

const styles = {
  card: { background: 'var(--bg-card)', padding: '28px' },
  cardHeader: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '4px',
    color: 'var(--text-muted)',
    marginBottom: '20px',
  },
  tableWrap: { overflowX: 'auto' },
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
  },
  tickerCell: {
    color: 'var(--accent-green)',
    fontWeight: 700,
    letterSpacing: '2px',
  },
}