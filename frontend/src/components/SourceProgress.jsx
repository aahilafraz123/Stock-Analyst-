import { useEffect, useState } from 'react'
import { STAGES, progressMessage, sourceList, summarizeSources } from '../state/analysisStream'
import { formatMs } from '../utils/format'

const STATUS_META = {
  pending: { color: 'var(--accent-blue)', label: 'Fetching' },
  ok: { color: 'var(--accent-green)', label: 'OK' },
  empty: { color: 'var(--accent-yellow)', label: 'No data' },
  error: { color: 'var(--accent-red)', label: 'Error' },
  skipped: { color: 'var(--text-muted)', label: 'Skipped' },
}

/** Seconds since mount, ticking while `running`. Mount once per analysis run. */
function useElapsedSeconds(running) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!running) return undefined
    const started = Date.now()
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 500)
    return () => clearInterval(timer)
  }, [running])
  return seconds
}

export function StatusDot({ status }) {
  if (status === 'pending') return <span className="spinner spinner--sm" aria-hidden="true" style={styles.spin} />
  const { color } = STATUS_META[status] || STATUS_META.error
  return (
    <span
      aria-hidden="true"
      style={{
        ...styles.dot,
        background: status === 'skipped' ? 'transparent' : color,
        border: `1.5px solid ${color}`,
        boxShadow: status === 'ok' ? `0 0 6px ${color}` : 'none',
      }}
    />
  )
}

/** Live view of the analysis pipeline: stages, current message and the 13 sources. */
export default function SourceProgress({ state, ticker }) {
  const running = state.phase === 'connecting' || state.phase === 'running'
  const elapsed = useElapsedSeconds(running)
  const counts = summarizeSources(state)
  const sources = sourceList(state)
  const stageIndex = STAGES.findIndex((s) => s.id === state.stage)
  const writing = state.stage === 'llm'
  const pct = counts.total ? Math.round((counts.settled / counts.total) * 100) : 0

  return (
    <section className="panel" aria-labelledby="progress-title" aria-busy={running}>
      <div className="panel-title">
        <span id="progress-title" style={styles.title}>
          <span style={styles.liveDot} aria-hidden="true" />
          {state.refresh ? 'REGENERATING' : 'RUNNING'} AI ANALYSIS · {ticker}
        </span>
        <span style={styles.elapsed} aria-label={`${elapsed} seconds elapsed`}>
          T+{String(Math.floor(elapsed / 60)).padStart(2, '0')}:{String(elapsed % 60).padStart(2, '0')}
        </span>
      </div>

      <ol style={styles.stages} aria-label="Pipeline stages">
        {STAGES.map((stage, i) => {
          const done = stageIndex > i
          const active = stageIndex === i
          const color = done ? 'var(--accent-green)' : active ? 'var(--text-primary)' : 'var(--text-muted)'
          return (
            <li
              key={stage.id}
              style={{ ...styles.stage, color, borderColor: active ? 'var(--accent-green)' : done ? 'rgba(0,255,136,0.35)' : 'var(--border)' }}
              aria-current={active ? 'step' : undefined}
            >
              <span style={styles.stageNum} className={done ? undefined : 'hide-sm'}>
                {done ? '✓' : `0${i + 1}`}
              </span>
              {stage.label.toUpperCase()}
            </li>
          )
        })}
      </ol>

      <div style={styles.message} role="status" aria-live="polite">
        <span style={styles.prompt}>&gt;</span>
        <span>{progressMessage(state)}</span>
        <span style={styles.cursor} aria-hidden="true">▌</span>
      </div>

      <div style={styles.barTrack} aria-hidden="true">
        <div style={{ ...styles.barFill, width: `${writing ? 100 : pct}%`, opacity: writing ? 0.35 : 1 }} />
        {writing && <div style={styles.barSweep} />}
      </div>

      <div style={styles.counts}>
        <span>
          SOURCES {counts.settled}/{counts.total}
        </span>
        {['ok', 'empty', 'error', 'skipped'].map((s) =>
          counts[s] ? (
            <span key={s} style={{ color: STATUS_META[s].color }}>
              {counts[s]} {STATUS_META[s].label.toUpperCase()}
            </span>
          ) : null,
        )}
      </div>

      <SourceGrid sources={sources} />
    </section>
  )
}

/** One row per data source with status dot, latency and error detail on hover. */
export function SourceGrid({ sources }) {
  return (
    <ul className="cell-grid" style={styles.grid} aria-label="Data sources">
      {sources.map((source) => (
        <SourceRow key={source.name} source={source} />
      ))}
    </ul>
  )
}

function SourceRow({ source }) {
  const meta = STATUS_META[source.status] || STATUS_META.error
  const hasDetail = Boolean(source.detail)
  return (
    <li
      className={hasDetail ? 'tip' : undefined}
      tabIndex={hasDetail ? 0 : undefined}
      style={{ ...styles.row, ...(source.status === 'pending' ? null : styles.rowSettled) }}
      data-status={source.status}
      aria-label={`${source.label}: ${meta.label}${source.ms != null ? `, ${formatMs(source.ms)}` : ''}${hasDetail ? `. ${source.detail}` : ''}`}
    >
      <StatusDot status={source.status} />
      <span style={{ ...styles.rowLabel, color: source.status === 'skipped' ? 'var(--text-muted)' : 'var(--text-secondary)' }}>
        {source.label}
      </span>
      {hasDetail && <span style={{ ...styles.info, color: meta.color }} aria-hidden="true">ⓘ</span>}
      <span style={{ ...styles.ms, color: source.status === 'pending' ? 'var(--text-muted)' : meta.color }}>
        {source.status === 'pending' ? '···' : source.status === 'skipped' || source.ms == null ? meta.label.toUpperCase() : formatMs(source.ms)}
      </span>
      {hasDetail && (
        <span className="tip__body" role="tooltip">
          <strong style={{ color: meta.color }}>{meta.label.toUpperCase()}</strong> · {source.detail}
        </span>
      )}
    </li>
  )
}

const mono = { fontFamily: 'var(--font-mono)' }

const styles = {
  title: { display: 'inline-flex', alignItems: 'center', gap: '10px', color: 'var(--accent-green)' },
  liveDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    background: 'var(--accent-green)',
    boxShadow: '0 0 8px var(--accent-green)',
    animation: 'pulse 1.2s ease-in-out infinite',
  },
  elapsed: { ...mono, fontSize: '11px', letterSpacing: '2px', color: 'var(--text-secondary)' },
  stages: {
    listStyle: 'none',
    display: 'grid',
    gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
    gap: '6px',
    marginBottom: '18px',
  },
  stage: {
    ...mono,
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '9px',
    letterSpacing: '1.5px',
    padding: '8px',
    borderWidth: '1px',
    borderStyle: 'solid',
    background: 'var(--bg-secondary)',
    minWidth: 0,
    overflow: 'hidden',
    whiteSpace: 'nowrap',
  },
  stageNum: { fontSize: '9px', opacity: 0.7 },
  message: {
    ...mono,
    display: 'flex',
    gap: '8px',
    alignItems: 'baseline',
    fontSize: '12px',
    color: 'var(--text-primary)',
    marginBottom: '12px',
    minHeight: '18px',
  },
  prompt: { color: 'var(--accent-green)' },
  cursor: { color: 'var(--accent-green)', animation: 'pulse 1s steps(1) infinite' },
  barTrack: {
    position: 'relative',
    height: '3px',
    background: 'var(--border)',
    overflow: 'hidden',
    marginBottom: '10px',
  },
  barFill: { height: '100%', background: 'var(--accent-green)', transition: 'width 0.3s ease' },
  barSweep: {
    position: 'absolute',
    inset: 0,
    width: '25%',
    background: 'linear-gradient(90deg, transparent, var(--accent-green), transparent)',
    animation: 'sweep 1.4s linear infinite',
  },
  counts: {
    ...mono,
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px 16px',
    fontSize: '9px',
    letterSpacing: '2px',
    color: 'var(--text-muted)',
    marginBottom: '16px',
  },
  grid: {
    listStyle: 'none',
    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '9px 12px',
    background: 'var(--bg-secondary)',
    minWidth: 0,
    transition: 'background 0.3s',
  },
  rowSettled: { background: 'var(--bg-card)' },
  rowLabel: { fontSize: '12px', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  info: { ...mono, fontSize: '10px', cursor: 'help' },
  ms: { ...mono, fontSize: '10px', letterSpacing: '0.5px', whiteSpace: 'nowrap' },
  dot: { width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0 },
  spin: { borderTopColor: 'var(--accent-blue)' },
}
