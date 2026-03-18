const fmt = (n, prefix = '') => n != null ? `${prefix}${Number(n).toLocaleString()}` : '—'
const fmtB = (n) => n != null ? `$${(n / 1e9).toFixed(2)}T` : '—'
const pct = (n) => n != null ? `${(n * 100).toFixed(1)}%` : '—'

export default function OverviewCard({ profile, ratios }) {
  if (!profile) return null
  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>OVERVIEW</div>
      <div style={styles.priceRow}>
        <span style={styles.price}>${fmt(profile.currentPrice)}</span>
        <span style={styles.mktCap}>{fmtB(profile.marketCap)} MARKET CAP</span>
      </div>
      <div style={styles.meta}>
        <MetaItem label="SECTOR" value={profile.sector} />
        <MetaItem label="INDUSTRY" value={profile.industry} />
        <MetaItem label="EMPLOYEES" value={fmt(profile.employees)} />
        <MetaItem label="COUNTRY" value={profile.country} />
      </div>
      <p style={styles.desc}>{profile.description?.slice(0, 300)}...</p>
    </div>
  )
}

function MetaItem({ label, value }) {
  return (
    <div style={styles.metaItem}>
      <span style={styles.metaLabel}>{label}</span>
      <span style={styles.metaValue}>{value || '—'}</span>
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
  priceRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '16px',
    marginBottom: '24px',
  },
  price: {
    fontFamily: 'var(--font-mono)',
    fontSize: '40px',
    fontWeight: 700,
    color: 'var(--accent-green)',
  },
  mktCap: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
  },
  meta: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    marginBottom: '20px',
    paddingBottom: '20px',
    borderBottom: '1px solid var(--border)',
  },
  metaItem: { display: 'flex', flexDirection: 'column', gap: '4px' },
  metaLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
  },
  metaValue: {
    fontFamily: 'var(--font-sans)',
    fontSize: '13px',
    color: 'var(--text-primary)',
    fontWeight: 600,
  },
  desc: {
    fontFamily: 'var(--font-sans)',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
  },
}