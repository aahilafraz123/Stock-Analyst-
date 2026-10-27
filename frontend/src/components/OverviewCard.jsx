import { formatInteger, formatMoneyCompact, formatPrice, formatSignedPct, toneColor } from '../utils/format'

export default function OverviewCard({ profile, price }) {
  if (!profile) return null
  const description = profile.description || ''
  const moves = price
    ? [
        { label: '1M', value: price.change1MonthPct },
        { label: '3M', value: price.change3MonthPct },
        { label: '6M', value: price.change6MonthPct },
        { label: 'VS 200D', value: price.priceVs200dmaPct },
      ]
    : []

  return (
    <section className="panel" aria-label="Company overview">
      <div className="panel-title">
        <span>OVERVIEW</span>
        {profile.exchange && <span>{profile.exchange}</span>}
      </div>
      <div style={styles.priceRow}>
        <span style={styles.price}>{formatPrice(profile.currentPrice ?? price?.currentPrice, profile.currency)}</span>
        <span style={styles.mktCap}>{formatMoneyCompact(profile.marketCap)} MARKET CAP</span>
      </div>

      {moves.some((m) => m.value != null) && (
        <div style={styles.moves}>
          {moves.map((m) => (
            <div key={m.label} style={styles.move}>
              <span style={styles.metaLabel}>{m.label}</span>
              <span style={{ ...styles.moveValue, color: toneColor(m.value) }}>{formatSignedPct(m.value)}</span>
            </div>
          ))}
        </div>
      )}

      <div style={styles.meta}>
        <MetaItem label="SECTOR" value={profile.sector} />
        <MetaItem label="INDUSTRY" value={profile.industry} />
        <MetaItem label="EMPLOYEES" value={profile.employees != null ? formatInteger(profile.employees) : null} />
        <MetaItem label="COUNTRY" value={profile.country} />
      </div>
      {description && (
        <p style={styles.desc}>{description.length > 300 ? `${description.slice(0, 300).trimEnd()}…` : description}</p>
      )}
    </section>
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
  priceRow: {
    display: 'flex',
    alignItems: 'baseline',
    flexWrap: 'wrap',
    gap: '4px 16px',
    marginBottom: '20px',
  },
  price: {
    fontFamily: 'var(--font-mono)',
    fontSize: 'clamp(30px, 6vw, 40px)',
    fontWeight: 700,
    color: 'var(--accent-green)',
  },
  mktCap: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
  },
  moves: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
    gap: '1px',
    background: 'var(--border)',
    border: '1px solid var(--border)',
    marginBottom: '20px',
  },
  move: { display: 'flex', flexDirection: 'column', gap: '4px', padding: '8px 10px', background: 'var(--bg-secondary)' },
  moveValue: { fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700 },
  meta: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: '12px',
    marginBottom: '20px',
    paddingBottom: '20px',
    borderBottom: '1px solid var(--border)',
  },
  metaItem: { display: 'flex', flexDirection: 'column', gap: '4px', minWidth: 0 },
  metaLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
  },
  metaValue: {
    fontSize: '13px',
    color: 'var(--text-primary)',
    fontWeight: 600,
    overflowWrap: 'anywhere',
  },
  desc: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
  },
}
