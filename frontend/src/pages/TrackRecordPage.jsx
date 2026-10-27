import { Link } from 'react-router-dom'
import { useRequest } from '../hooks/useRequest'
import { getErrorDetail, getTrackRecord } from '../services/api'
import ErrorNotice from '../components/ErrorNotice'
import Loader from '../components/Loader'
import { formatDate, formatPrice, formatSignedPct, recColor, toneColor } from '../utils/format'

const MIN_AGE_DAYS = 7

/** How every stored recommendation has done against SPY since it was issued. */
export default function TrackRecordPage() {
  const record = useRequest('track-record', (signal) => getTrackRecord({ minAgeDays: MIN_AGE_DAYS, signal }))
  const data = record.data
  const benchmark = data?.benchmark || 'SPY'
  const reports = data?.reports || []

  return (
    <div className="page">
      <header className="topbar">
        <Link to="/" className="btn">
          ← TERMINAL
        </Link>
        <h1 className="topbar__title">TRACK RECORD</h1>
        <span className="topbar__name hide-sm">Every AI recommendation, scored against {benchmark}</span>
      </header>

      <main className="track-page__body">
        {record.loading && <Loader label="SCORING REPORTS" sub={`Comparing each recommendation with ${benchmark}`} />}
        {record.error && (
          <div className="panel">
            <ErrorNotice title="TRACK RECORD UNAVAILABLE" detail={getErrorDetail(record.error)} onRetry={record.reload} />
          </div>
        )}

        {data && (
          <>
            <div className="kpi-grid">
              <Kpi
                label="HIT RATE"
                value={data.hitRate != null ? `${Math.round(data.hitRate * 100)}%` : '—'}
                sub={`${data.scoredReports ?? 0} scored report${data.scoredReports === 1 ? '' : 's'}`}
                color={data.hitRate == null ? undefined : data.hitRate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)'}
              />
              <Kpi
                label={`AVG EXCESS VS ${benchmark}`}
                value={formatSignedPct(data.avgExcessReturnPct, 2)}
                sub="mean of report return − benchmark return"
                color={toneColor(data.avgExcessReturnPct)}
              />
              <Kpi label="REPORTS TRACKED" value={reports.length} sub={`${reports.filter((r) => !r.matured).length} too early to score`} />
              <Kpi label="SCORING WINDOW" value={`≥ ${data.minAgeDays ?? MIN_AGE_DAYS} DAYS`} sub={`benchmark: ${benchmark}`} />
            </div>

            <section className="panel" aria-labelledby="reports-title">
              <div className="panel-title">
                <span id="reports-title">SCORED RECOMMENDATIONS</span>
              </div>
              {reports.length === 0 ? (
                <p style={styles.muted}>
                  No reports yet. <Link to="/" style={styles.link}>Run an analysis</Link> and it will appear here once it is{' '}
                  {data.minAgeDays ?? MIN_AGE_DAYS} days old.
                </p>
              ) : (
                <div className="table-wrap">
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        {['TICKER', 'DATE', 'REC', 'CONF', 'ENTRY', 'RETURN', `${benchmark}`, 'EXCESS', 'HIT'].map((h) => (
                          <th key={h} style={styles.th} scope="col">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {reports.map((r) => (
                        <tr key={r.id} style={styles.row}>
                          <td style={{ ...styles.td, ...styles.ticker }}>
                            <Link to={`/stock/${r.ticker}`}>{r.ticker}</Link>
                          </td>
                          <td style={styles.td}>{formatDate(r.createdAt)}</td>
                          <td style={{ ...styles.td, color: recColor(r.recommendation), fontWeight: 700 }}>{r.recommendation}</td>
                          <td style={styles.td}>{r.confidence ?? '—'}</td>
                          <td style={styles.td}>{formatPrice(r.price)}</td>
                          <td style={{ ...styles.td, color: toneColor(r.returnPct) }}>{formatSignedPct(r.returnPct, 2)}</td>
                          <td style={{ ...styles.td, color: toneColor(r.benchmarkReturnPct) }}>{formatSignedPct(r.benchmarkReturnPct, 2)}</td>
                          <td style={{ ...styles.td, color: toneColor(r.excessReturnPct), fontWeight: 700 }}>
                            {formatSignedPct(r.excessReturnPct, 2)}
                          </td>
                          <td style={styles.td}>
                            <HitCell report={r} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}

        <section className="panel" aria-labelledby="method-title">
          <div className="panel-title">
            <span id="method-title">HOW REPORTS ARE SCORED</span>
          </div>
          <div className="two-col">
            <div style={styles.prose}>
              <p>
                Every completed analysis is stored with the share price and the {benchmark} price at the moment it was
                generated. Returns are measured from those prices to the latest close; the excess return is the
                stock&apos;s return minus {benchmark}&apos;s over the same period.
              </p>
              <p>
                Reports younger than {data?.minAgeDays ?? MIN_AGE_DAYS} days are listed but marked <em>too early</em> and
                left out of the hit rate and average.
              </p>
            </div>
            <ul style={styles.rules}>
              <li>
                <b style={{ color: 'var(--accent-green)' }}>BUY</b> hits if the stock beat {benchmark}.
              </li>
              <li>
                <b style={{ color: 'var(--accent-red)' }}>SELL</b> hits if the stock lagged {benchmark}.
              </li>
              <li>
                <b style={{ color: 'var(--accent-yellow)' }}>HOLD</b> hits if the stock finished within ±5% of {benchmark}.
              </li>
            </ul>
          </div>
          <p style={styles.disclaimer} role="note">
            <b>Not investment advice.</b> These figures describe a small, unaudited sample of AI-generated reports and
            ignore dividends, fees and taxes. Past performance does not predict future results. Do not make investment
            decisions based on this page.
          </p>
        </section>
      </main>
    </div>
  )
}

function Kpi({ label, value, sub, color }) {
  return (
    <div className="panel" style={styles.kpi}>
      <span style={styles.kpiLabel}>{label}</span>
      <span style={{ ...styles.kpiValue, color: color || 'var(--text-primary)' }}>{value}</span>
      {sub && <span style={styles.kpiSub}>{sub}</span>}
    </div>
  )
}

function HitCell({ report }) {
  if (!report.matured) return <span style={styles.early} title={`Scored after ${MIN_AGE_DAYS} days`}>too early</span>
  if (report.hit === true) return <span style={{ ...styles.mark, color: 'var(--accent-green)' }} aria-label="hit">✓</span>
  if (report.hit === false) return <span style={{ ...styles.mark, color: 'var(--accent-red)' }} aria-label="miss">✗</span>
  return <span style={styles.early}>—</span>
}

const mono = { fontFamily: 'var(--font-mono)' }

const styles = {
  kpi: { display: 'flex', flexDirection: 'column', gap: '8px' },
  kpiLabel: { ...mono, fontSize: '9px', letterSpacing: '2px', color: 'var(--text-muted)' },
  kpiValue: { ...mono, fontSize: 'clamp(22px, 4vw, 32px)', fontWeight: 700 },
  kpiSub: { ...mono, fontSize: '9px', color: 'var(--text-muted)', lineHeight: 1.4 },
  muted: { fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 },
  link: { color: 'var(--accent-green)' },
  table: { width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)' },
  th: { fontSize: '9px', letterSpacing: '2px', color: 'var(--text-muted)', padding: '8px 12px', textAlign: 'left', borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap', fontWeight: 400 },
  row: { borderBottom: '1px solid var(--border)' },
  td: { fontSize: '12px', color: 'var(--text-secondary)', padding: '10px 12px', whiteSpace: 'nowrap' },
  ticker: { color: 'var(--accent-green)', fontWeight: 700, letterSpacing: '2px' },
  mark: { fontSize: '15px', fontWeight: 700 },
  early: { ...mono, fontSize: '10px', color: 'var(--text-muted)', fontStyle: 'italic' },
  prose: { display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px', lineHeight: 1.7, color: 'var(--text-secondary)' },
  rules: { listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', lineHeight: 1.6, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' },
  disclaimer: {
    marginTop: '20px',
    padding: '12px 14px',
    border: '1px solid rgba(255, 204, 0, 0.35)',
    background: 'rgba(255, 204, 0, 0.05)',
    fontSize: '12px',
    lineHeight: 1.6,
    color: 'var(--text-secondary)',
  },
}
