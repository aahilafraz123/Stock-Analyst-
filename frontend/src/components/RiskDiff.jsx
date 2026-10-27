import { useState } from 'react'
import { useRequest } from '../hooks/useRequest'
import { getErrorDetail, getRiskDiff } from '../services/api'
import { formatDate } from '../utils/format'
import ErrorNotice from './ErrorNotice'

const GROUPS = [
  { key: 'added', label: 'ADDED', marker: '+', color: 'var(--accent-red)', hint: 'New in the latest 10-K' },
  { key: 'escalated', label: 'ESCALATED', marker: '▲', color: 'var(--accent-yellow)', hint: 'Language strengthened' },
  { key: 'deemphasized', label: 'DE-EMPHASIZED', marker: '▼', color: 'var(--accent-blue)', hint: 'Language softened' },
  { key: 'removed', label: 'REMOVED', marker: '−', color: 'var(--accent-green)', hint: 'Dropped from the latest 10-K' },
]

/** Year-over-year comparison of the Risk Factors section in the last two 10-Ks. */
export default function RiskDiff({ ticker }) {
  const [requested, setRequested] = useState(false)
  const diff = useRequest(requested ? ticker : null, (signal) => getRiskDiff(ticker, { signal }))
  const data = diff.data

  return (
    <section className="panel" aria-labelledby="riskdiff-title">
      <div className="panel-title">
        <span id="riskdiff-title">RISK FACTORS · YEAR OVER YEAR</span>
        {data?.cached && <span style={styles.cached}>CACHED</span>}
      </div>

      {!requested && (
        <div style={styles.intro}>
          <p style={styles.introText}>
            Compares Item 1A of the two most recent 10-K filings and lists the risks that were added, removed,
            escalated or softened, each backed by a quote checked against the filing text.
          </p>
          <button type="button" className="btn" onClick={() => setRequested(true)}>
            ⇄ COMPARE RISK FACTORS YOY
          </button>
        </div>
      )}

      {diff.loading && (
        <div style={styles.loading} role="status" aria-live="polite">
          <span className="spinner spinner--sm" aria-hidden="true" />
          Reading both 10-K Risk Factors sections and comparing them…
        </div>
      )}

      {diff.error && (
        <ErrorNotice title="RISK COMPARISON UNAVAILABLE" detail={getErrorDetail(diff.error)} onRetry={diff.reload} compact />
      )}

      {data && (
        <div style={styles.result}>
          <div style={styles.filings}>
            <FilingLink label="LATEST" filing={data.newer} />
            <span style={styles.vs}>vs</span>
            <FilingLink label="PRIOR" filing={data.older} />
          </div>

          {data.summary && <p style={styles.summary}>{data.summary}</p>}
          {data.truncated && (
            <p style={styles.note}>Note: a Risk Factors section was truncated for length, so the comparison may be incomplete.</p>
          )}

          <div className="two-col" style={{ gap: '20px' }}>
            {GROUPS.map((group) => (
              <ChangeGroup key={group.key} group={group} items={data[group.key] || []} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function FilingLink({ label, filing }) {
  if (!filing) return null
  const text = `${label} 10-K · filed ${formatDate(filing.filingDate)}`
  return filing.url ? (
    <a href={filing.url} target="_blank" rel="noopener noreferrer" style={styles.filing}>
      {text} ↗
    </a>
  ) : (
    <span style={styles.filing}>{text}</span>
  )
}

function ChangeGroup({ group, items }) {
  return (
    <div style={styles.group}>
      <div style={{ ...styles.groupHead, color: group.color }} title={group.hint}>
        <span>
          {group.marker} {group.label}
        </span>
        <span style={styles.groupCount}>{items.length}</span>
      </div>
      {items.length === 0 && <span style={styles.none}>No changes identified.</span>}
      <ul style={styles.items}>
        {items.map((item, i) => (
          <li key={i} style={{ ...styles.item, borderLeftColor: group.color }}>
            <span style={styles.itemTitle}>{item.title}</span>
            {item.detail && <span style={styles.itemDetail}>{item.detail}</span>}
            {item.quote && (
              <blockquote style={styles.quote}>
                “{item.quote.trim()}”
                <span
                  style={item.quoteVerified ? styles.verified : styles.unverified}
                  title={
                    item.quoteVerified
                      ? 'Quote found verbatim in the filing text'
                      : 'Quote could not be matched verbatim in the filing text'
                  }
                >
                  {item.quoteVerified ? '✓ verified quote' : 'unverified'}
                </span>
              </blockquote>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

const mono = { fontFamily: 'var(--font-mono)' }
const badge = { ...mono, display: 'inline-block', marginLeft: '8px', fontStyle: 'normal', fontSize: '9px', letterSpacing: '1px', padding: '1px 6px', whiteSpace: 'nowrap' }

const styles = {
  cached: { ...mono, fontSize: '9px', letterSpacing: '2px', color: 'var(--accent-yellow)' },
  intro: { display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '14px' },
  introText: { fontSize: '12px', lineHeight: 1.6, color: 'var(--text-secondary)' },
  loading: { ...mono, display: 'flex', alignItems: 'center', gap: '10px', fontSize: '11px', color: 'var(--accent-blue)' },
  result: { display: 'flex', flexDirection: 'column', gap: '16px' },
  filings: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px 10px' },
  filing: { ...mono, fontSize: '10px', letterSpacing: '1px', color: 'var(--text-secondary)', border: '1px solid var(--border-bright)', padding: '4px 8px' },
  vs: { ...mono, fontSize: '10px', color: 'var(--text-muted)' },
  summary: { fontSize: '13px', lineHeight: 1.7, color: 'var(--text-primary)' },
  note: { ...mono, fontSize: '10px', color: 'var(--accent-yellow)' },
  group: { display: 'flex', flexDirection: 'column', gap: '10px', minWidth: 0 },
  groupHead: { ...mono, display: 'flex', justifyContent: 'space-between', fontSize: '10px', letterSpacing: '3px', paddingBottom: '6px', borderBottom: '1px solid var(--border)' },
  groupCount: { color: 'var(--text-muted)' },
  none: { fontSize: '11px', color: 'var(--text-muted)' },
  items: { listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '12px' },
  item: { display: 'flex', flexDirection: 'column', gap: '6px', paddingLeft: '10px', borderLeft: '2px solid' },
  itemTitle: { fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' },
  itemDetail: { fontSize: '12px', lineHeight: 1.6, color: 'var(--text-secondary)' },
  quote: { fontSize: '11px', lineHeight: 1.6, fontStyle: 'italic', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '8px 10px', overflowWrap: 'anywhere' },
  verified: { ...badge, color: 'var(--accent-green)', border: '1px solid rgba(0, 255, 136, 0.35)' },
  unverified: { ...badge, color: 'var(--accent-yellow)', border: '1px solid rgba(255, 204, 0, 0.35)' },
}
