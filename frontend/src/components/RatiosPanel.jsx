const fmt = (n, decimals = 2) => n != null ? Number(n).toFixed(decimals) : '—'
const pct = (n) => n != null ? `${(n * 100).toFixed(1)}%` : '—'

export default function RatiosPanel({ ratios }) {
  if (!ratios) return null

  const items = [
    { label: 'P/E RATIO', value: fmt(ratios.peRatio) },
    { label: 'FORWARD P/E', value: fmt(ratios.forwardPE) },
    { label: 'P/B RATIO', value: fmt(ratios.pbRatio) },
    { label: 'EV/EBITDA', value: fmt(ratios.evToEbitda) },
    { label: 'PRICE/SALES', value: fmt(ratios.priceToSales) },
    { label: 'DEBT/EQUITY', value: fmt(ratios.debtToEquity) },
    { label: 'CURRENT RATIO', value: fmt(ratios.currentRatio) },
    { label: 'GROSS MARGIN', value: pct(ratios.grossMargin) },
    { label: 'OP. MARGIN', value: pct(ratios.operatingMargin) },
    { label: 'NET MARGIN', value: pct(ratios.profitMargin) },
    { label: 'ROE', value: pct(ratios.returnOnEquity) },
    { label: 'ROA', value: pct(ratios.returnOnAssets) },
    { label: 'REV. GROWTH', value: pct(ratios.revenueGrowth) },
    { label: 'EPS GROWTH', value: pct(ratios.earningsGrowth) },
  ]

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>FINANCIAL RATIOS</div>
      <div style={styles.grid}>
        {items.map(({ label, value }) => (
          <div key={label} style={styles.item}>
            <span style={styles.label}>{label}</span>
            <span style={styles.value}>{value}</span>
          </div>
        ))}
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
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '1px',
    background: 'var(--border)',
    border: '1px solid var(--border)',
  },
  item: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 14px',
    background: 'var(--bg-card)',
  },
  label: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    color: 'var(--text-muted)',
    letterSpacing: '1px',
  },
  value: {
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    color: 'var(--text-primary)',
    fontWeight: 700,
  },
}