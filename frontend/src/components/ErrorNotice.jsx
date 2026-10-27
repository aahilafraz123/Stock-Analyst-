/** Compact error block with the backend's message and an optional retry. */
export default function ErrorNotice({ title = 'ERROR', detail, meta, onRetry, retryLabel = 'RETRY', compact = false }) {
  return (
    <div role="alert" style={{ ...styles.box, ...(compact ? styles.compact : null) }}>
      <div style={styles.head}>
        <span style={styles.code}>✕ {title}</span>
        {meta && <span style={styles.meta}>{meta}</span>}
      </div>
      {detail && <p style={styles.detail}>{detail}</p>}
      {onRetry && (
        <div>
          <button type="button" className="btn btn--small" onClick={onRetry}>
            ↻ {retryLabel}
          </button>
        </div>
      )}
    </div>
  )
}

const styles = {
  box: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    padding: '16px 18px',
    border: '1px solid rgba(255, 68, 102, 0.35)',
    background: 'rgba(255, 68, 102, 0.05)',
  },
  compact: { padding: '10px 12px', gap: '6px' },
  head: { display: 'flex', flexWrap: 'wrap', gap: '6px 16px', alignItems: 'baseline' },
  code: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '3px',
    color: 'var(--accent-red)',
  },
  meta: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    letterSpacing: '1px',
    color: 'var(--text-muted)',
  },
  detail: {
    fontSize: '13px',
    lineHeight: 1.6,
    color: 'var(--text-secondary)',
    overflowWrap: 'anywhere',
  },
}
