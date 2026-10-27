import AnalysisReport from './AnalysisReport'
import ErrorNotice from './ErrorNotice'
import Loader from './Loader'
import SourceProgress, { SourceGrid } from './SourceProgress'
import { sourceList } from '../state/analysisStream'
import { formatDateTime } from '../utils/format'
import { getErrorDetail } from '../services/api'

/**
 * The right-hand analysis slot: live progress, the finished report, a failure
 * with retry, or an archived report picked from the history panel.
 */
export default function AnalysisPanel({ ticker, stream, onRestart, archived, onCloseArchived }) {
  if (archived) {
    return (
      <div>
        <div style={styles.banner} role="status">
          <span>
            ARCHIVED REPORT #{archived.id}
            {archived.data?.generatedAt && <> · {formatDateTime(archived.data.generatedAt)}</>}
          </span>
          <button type="button" className="btn btn--small" onClick={onCloseArchived}>
            ← BACK TO LATEST
          </button>
        </div>
        {archived.loading && <Loader label="LOADING REPORT" />}
        {archived.error && (
          <div className="panel">
            <ErrorNotice
              title="COULD NOT LOAD REPORT"
              detail={getErrorDetail(archived.error)}
              onRetry={archived.reload}
            />
          </div>
        )}
        {archived.data && <AnalysisReport response={archived.data} />}
      </div>
    )
  }

  if (stream.phase === 'done' && stream.response) {
    return <AnalysisReport response={stream.response} onRegenerate={() => onRestart({ refresh: true })} />
  }

  if (stream.phase === 'error') {
    const { error } = stream
    const reached = sourceList(stream).filter((s) => s.status !== 'pending')
    const meta = [error.code?.replace(/_/g, ' ').toUpperCase(), error.status, error.source].filter(Boolean).join(' · ')
    return (
      <section className="panel" aria-labelledby="analysis-failed-title">
        <div className="panel-title">
          <span id="analysis-failed-title">AI ANALYSIS REPORT</span>
        </div>
        <ErrorNotice
          title="AI ANALYSIS FAILED"
          meta={meta}
          detail={error.detail}
          onRetry={() => onRestart({ refresh: stream.refresh })}
        />
        {reached.length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <div style={styles.subLabel}>SOURCES REACHED BEFORE THE FAILURE</div>
            <SourceGrid sources={reached} />
          </div>
        )}
      </section>
    )
  }

  return <SourceProgress key={stream.runId} state={stream} ticker={ticker} />
}

const styles = {
  banner: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: '8px 16px',
    padding: '10px var(--panel-pad)',
    background: 'rgba(68, 136, 255, 0.08)',
    borderBottom: '1px solid rgba(68, 136, 255, 0.3)',
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '2px',
    color: 'var(--accent-blue)',
  },
  subLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    letterSpacing: '3px',
    color: 'var(--text-muted)',
    marginBottom: '10px',
  },
}
