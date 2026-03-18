export default function Loader({ ticker }) {
  return (
    <div style={styles.page}>
      <div style={styles.box}>
        <div style={styles.spinner} />
        <div style={styles.label}>ANALYZING {ticker}</div>
        <div style={styles.sub}>Fetching filings · Scanning news · Running AI model</div>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--bg-primary)',
  },
  box: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '20px',
  },
  spinner: {
    width: '48px',
    height: '48px',
    border: '2px solid var(--border-bright)',
    borderTop: '2px solid var(--accent-green)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  label: {
    fontFamily: 'var(--font-mono)',
    fontSize: '14px',
    color: 'var(--accent-green)',
    letterSpacing: '4px',
  },
  sub: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-muted)',
    letterSpacing: '1px',
  },
}