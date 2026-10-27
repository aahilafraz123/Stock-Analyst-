/** Inline loading state for a panel. */
export default function Loader({ label = 'LOADING', sub, minHeight = 220 }) {
  return (
    <div className="panel" style={{ ...styles.box, minHeight }} role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <div style={styles.label}>{label}</div>
      {sub && <div style={styles.sub}>{sub}</div>}
    </div>
  )
}

const styles = {
  box: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    textAlign: 'center',
  },
  label: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--accent-green)',
    letterSpacing: '4px',
  },
  sub: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
    letterSpacing: '1px',
  },
}
