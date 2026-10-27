import { useRequest } from '../hooks/useRequest'
import { getErrorDetail, getReports } from '../services/api'
import { formatDateTime, formatPrice, recColor } from '../utils/format'

/**
 * Past reports for the ticker. `refreshKey` changes when a new report is stored,
 * which refetches the list. `activeId` marks the report currently displayed.
 */
export default function ReportHistory({ ticker, refreshKey, activeId, onSelect }) {
  const reports = useRequest(`${ticker}:${refreshKey ?? ''}`, (signal) => getReports(ticker, { limit: 10, signal }))
  const list = Array.isArray(reports.data) ? reports.data : []

  return (
    <section className="panel" aria-labelledby="history-title">
      <div className="panel-title">
        <span id="history-title">REPORT HISTORY</span>
        <span>{list.length ? `${list.length} SAVED` : ''}</span>
      </div>

      {reports.loading && <p style={styles.muted}>Loading saved reports…</p>}
      {reports.error && (
        <p style={styles.error}>
          {getErrorDetail(reports.error)}{' '}
          <button type="button" className="btn btn--small" onClick={reports.reload}>
            RETRY
          </button>
        </p>
      )}
      {!reports.loading && !reports.error && list.length === 0 && (
        <p style={styles.muted}>No saved reports for {ticker} yet. Each completed analysis is stored here.</p>
      )}

      {list.length > 0 && (
        <ul style={styles.list}>
          {list.map((r) => {
            const active = r.id === activeId
            return (
              <li key={r.id}>
                <button
                  type="button"
                  style={{ ...styles.row, ...(active ? styles.rowActive : null) }}
                  aria-current={active ? 'true' : undefined}
                  onClick={() => onSelect(r.id)}
                >
                  <span style={styles.date}>{formatDateTime(r.createdAt)}</span>
                  <span style={{ ...styles.rec, color: recColor(r.recommendation) }}>{r.recommendation || '—'}</span>
                  <span style={styles.conf}>{r.confidence != null ? `${r.confidence}%` : '—'}</span>
                  <span style={styles.price}>{formatPrice(r.price)}</span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

const mono = { fontFamily: 'var(--font-mono)' }

const styles = {
  muted: { fontSize: '12px', lineHeight: 1.6, color: 'var(--text-muted)' },
  error: { fontSize: '12px', lineHeight: 1.6, color: 'var(--accent-red)', display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' },
  list: { listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '1px', background: 'var(--border)', border: '1px solid var(--border)' },
  row: {
    ...mono,
    width: '100%',
    display: 'grid',
    gridTemplateColumns: 'minmax(0, 1fr) 44px 40px 76px',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 12px',
    background: 'var(--bg-card)',
    borderStyle: 'none none none solid',
    borderWidth: '0 0 0 2px',
    borderColor: 'transparent',
    cursor: 'pointer',
    textAlign: 'left',
    fontSize: '11px',
    color: 'var(--text-secondary)',
  },
  rowActive: { background: 'var(--bg-card-hover)', borderColor: 'var(--accent-green)' },
  date: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '10px' },
  rec: { fontWeight: 700, letterSpacing: '1px' },
  conf: { color: 'var(--text-muted)', textAlign: 'right' },
  price: { textAlign: 'right', color: 'var(--text-primary)' },
}
