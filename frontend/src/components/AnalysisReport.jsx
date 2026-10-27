import { Citations } from './CitationChip'
import { StatusDot } from './SourceProgress'
import {
  formatDateTime,
  formatInteger,
  formatMs,
  formatPrice,
  formatSignedPct,
  recColor,
  signalColor,
  toneColor,
} from '../utils/format'

const healthColor = (a) =>
  ({ STRONG: 'var(--accent-green)', WEAK: 'var(--accent-red)', MODERATE: 'var(--accent-yellow)' })[a] ||
  'var(--text-primary)'

const valuationColor = (a) =>
  ({ UNDERVALUED: 'var(--accent-green)', OVERVALUED: 'var(--accent-red)', 'FAIRLY VALUED': 'var(--accent-yellow)' })[a] ||
  'var(--text-primary)'

/** Renders an AnalysisResponse (`response.report` + sources, metrics and meta). */
export default function AnalysisReport({ response, onRegenerate }) {
  const report = response?.report
  if (!report) return null

  const sources = Object.fromEntries((response.sources || []).map((s) => [s.id, s]))
  const metrics = response.metrics || {}
  const meta = response.meta || {}

  return (
    <article className="panel" aria-labelledby="report-title">
      <div className="panel-title">
        <span id="report-title">AI ANALYSIS REPORT</span>
        <span style={styles.generated}>
          {meta.cached && <span style={styles.cachedBadge}>CACHED</span>}
          {formatDateTime(response.generatedAt || response.analysisDate)}
        </span>
      </div>

      <div className="tile-grid" style={styles.tiles}>
        <Tile label="SIGNAL" value={report.overallSignal} color={signalColor(report.overallSignal)} />
        <Tile label="RECOMMENDATION" value={report.recommendation} color={recColor(report.recommendation)} />
        <Tile label="CONFIDENCE" value={report.confidenceScore != null ? `${report.confidenceScore}/100` : '—'}>
          <Meter value={(report.confidenceScore ?? 0) / 100} color="var(--accent-blue)" />
        </Tile>
        <Tile
          label="VALUATION"
          value={report.valuation?.assessment}
          color={valuationColor(report.valuation?.assessment)}
        />
        <Tile
          label="FINANCIAL HEALTH"
          value={report.financialHealth?.assessment}
          color={healthColor(report.financialHealth?.assessment)}
        />
        <Tile label="ANALYST TARGET" value={formatPrice(metrics.targetMeanPrice)} color="var(--text-primary)">
          {metrics.targetMeanPrice != null && (
            <span style={styles.tileSub}>
              <span style={{ color: toneColor(metrics.impliedUpsidePct) }}>{formatSignedPct(metrics.impliedUpsidePct)}</span>
              {metrics.numberOfAnalysts ? ` · ${metrics.numberOfAnalysts} analysts` : ''}
            </span>
          )}
        </Tile>
      </div>

      <Section label="EXECUTIVE SUMMARY" claim={report.summary} sources={sources} lead />
      <Section label="RECOMMENDATION REASONING" claim={report.recommendationReasoning} sources={sources} />
      <Section label="VALUATION" claim={toClaim(report.valuation)} sources={sources} />
      <Section label="FINANCIAL HEALTH" claim={toClaim(report.financialHealth)} sources={sources} />

      <div className="two-col" style={styles.divided}>
        <ClaimList label="STRENGTHS" items={report.strengths} sources={sources} color="var(--accent-green)" marker="▸" />
        <ClaimList label="RISKS" items={report.risks} sources={sources} color="var(--accent-red)" marker="▸" />
      </div>
      <div style={styles.divided}>
        <ClaimList label="CATALYSTS" items={report.catalysts} sources={sources} color="var(--accent-blue)" marker="◆" />
      </div>

      <Section label="MANAGEMENT TONE" claim={report.managementTone} sources={sources} />
      <Section label="PRICE CONTEXT & MOMENTUM" claim={report.priceContext} sources={sources} />
      <Section label="WALL STREET CONSENSUS" claim={report.analystConsensus} sources={sources} />
      <Section label="COMPETITIVE POSITION" claim={report.competitivePosition} sources={sources} />
      <Section label="RECENT NEWS IMPACT" claim={report.recentNewsImpact} sources={sources} />

      <SourceIndex sources={response.sources} />
      <ReportMeta meta={meta} onRegenerate={onRegenerate} />
    </article>
  )
}

/** `{assessment, reasoning, sources}` → `{text, sources}` */
const toClaim = (block) => (block?.reasoning ? { text: block.reasoning, sources: block.sources } : null)

function Tile({ label, value, color, children }) {
  return (
    <div style={styles.tile}>
      <span style={styles.tileLabel}>{label}</span>
      <span style={{ ...styles.tileValue, color: color || 'var(--text-primary)' }}>{value || '—'}</span>
      {children}
    </div>
  )
}

function Meter({ value, color }) {
  const pct = Math.max(0, Math.min(1, value || 0)) * 100
  return (
    <span style={styles.meter} aria-hidden="true">
      <span style={{ ...styles.meterFill, width: `${pct}%`, background: color }} />
    </span>
  )
}

function Section({ label, claim, sources, lead = false }) {
  if (!claim?.text) return null
  return (
    <section style={styles.section}>
      <h3 style={styles.sectionLabel}>{label}</h3>
      <p style={{ ...styles.sectionContent, ...(lead ? styles.lead : null) }}>
        {claim.text}
        <Citations ids={claim.sources} sources={sources} />
      </p>
    </section>
  )
}

function ClaimList({ label, items, sources, color, marker }) {
  const list = (items || []).filter((i) => i?.text)
  return (
    <section style={styles.listSection}>
      <h3 style={styles.sectionLabel}>{label}</h3>
      {list.length === 0 && <span style={styles.none}>None identified.</span>}
      <ul style={styles.list}>
        {list.map((item, i) => (
          <li key={i} style={styles.listItem}>
            <span style={{ color, flexShrink: 0 }} aria-hidden="true">
              {marker}
            </span>
            <span style={styles.listText}>
              {item.text}
              <Citations ids={item.sources} sources={sources} />
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function SourceIndex({ sources }) {
  if (!sources?.length) return null
  return (
    <details style={styles.details}>
      <summary style={styles.summary}>EVIDENCE · {sources.length} SOURCES</summary>
      <ol style={styles.sourceList}>
        {sources.map((s) => (
          <li key={s.id} style={styles.sourceItem}>
            <span style={styles.sourceId}>{s.id}</span>
            <span style={{ minWidth: 0 }}>
              {s.url ? (
                <a href={s.url} target="_blank" rel="noopener noreferrer" style={styles.sourceLink}>
                  {s.label} ↗
                </a>
              ) : (
                <span style={styles.sourceLabel}>{s.label}</span>
              )}
              {s.date && <span style={styles.sourceDate}> · {s.date}</span>}
            </span>
          </li>
        ))}
      </ol>
    </details>
  )
}

function ReportMeta({ meta, onRegenerate }) {
  const citations = meta.citations || {}
  const retrieval = meta.retrieval || {}
  const grounded = typeof citations.groundedness === 'number' ? citations.groundedness : null
  const groundColor =
    grounded == null ? 'var(--text-secondary)' : grounded >= 0.9 ? 'var(--accent-green)' : grounded >= 0.7 ? 'var(--accent-yellow)' : 'var(--accent-red)'
  const unavailable = (meta.sourceStatus || []).filter((s) => s.status === 'error' || s.status === 'skipped')
  const docCount = retrieval.documents?.length ?? 0

  return (
    <footer style={styles.meta} aria-label="Report metadata">
      <div className="tile-grid">
        <MetaItem label="MODEL" value={meta.model} />
        <MetaItem
          label="TOKENS IN / OUT"
          value={`${formatInteger(meta.inputTokens)} / ${formatInteger(meta.outputTokens)}`}
          sub={meta.cacheReadTokens ? `${formatInteger(meta.cacheReadTokens)} cache read` : null}
        />
        <MetaItem
          label="LATENCY"
          value={formatMs(meta.latencyMs)}
          sub={meta.totalLatencyMs ? `${formatMs(meta.totalLatencyMs)} end-to-end` : null}
        />
        <MetaItem
          label="RETRIEVAL"
          value={retrieval.mode ? retrieval.mode.toUpperCase() : '—'}
          sub={retrieval.embedder || (retrieval.mode === 'bm25' ? 'lexical only' : null)}
        />
        <MetaItem
          label="CHUNKS"
          value={formatInteger(retrieval.chunks)}
          sub={docCount ? `from ${docCount} document${docCount === 1 ? '' : 's'}` : null}
        />
        <MetaItem
          label="GROUNDEDNESS"
          value={grounded == null ? '—' : `${Math.round(grounded * 100)}%`}
          color={groundColor}
          sub={
            citations.claims != null
              ? `${citations.groundedClaims ?? 0}/${citations.claims} claims cited${citations.invalidRemoved ? ` · ${citations.invalidRemoved} invalid removed` : ''}`
              : null
          }
        >
          {grounded != null && <Meter value={grounded} color={groundColor} />}
        </MetaItem>
      </div>

      <div style={styles.metaBar}>
        {meta.cached ? (
          <span style={styles.cachedPill} title="Served from a report generated in the last 6 hours">
            ● CACHED REPORT
          </span>
        ) : (
          <span style={styles.freshPill}>● FRESH REPORT</span>
        )}
        {meta.reportId != null && <span style={styles.reportId}>REPORT #{meta.reportId}</span>}
        <span style={{ flex: 1 }} />
        {onRegenerate && (
          <button type="button" className="btn btn--small" onClick={onRegenerate}>
            ↻ REGENERATE
          </button>
        )}
      </div>

      {unavailable.length > 0 && (
        <div style={styles.unavailable}>
          <span style={styles.unavailableLabel}>UNAVAILABLE SOURCES ({unavailable.length})</span>
          <ul style={styles.unavailableList}>
            {unavailable.map((s) => (
              <li key={s.name} className="tip" tabIndex={0} style={styles.unavailableItem}>
                <StatusDot status={s.status} />
                <span>{s.label || s.name}</span>
                <span style={{ color: s.status === 'error' ? 'var(--accent-red)' : 'var(--text-muted)' }}>
                  {s.status.toUpperCase()}
                </span>
                {s.detail && (
                  <span className="tip__body" role="tooltip">
                    {s.detail}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </footer>
  )
}

function MetaItem({ label, value, sub, color, children }) {
  return (
    <div style={styles.metaItem}>
      <span style={styles.tileLabel}>{label}</span>
      <span style={{ ...styles.metaValue, color: color || 'var(--text-primary)' }}>{value || '—'}</span>
      {children}
      {sub && <span style={styles.metaSub}>{sub}</span>}
    </div>
  )
}

const mono = { fontFamily: 'var(--font-mono)' }
const label = { ...mono, fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '2px' }

const styles = {
  generated: { ...mono, display: 'inline-flex', gap: '10px', alignItems: 'center', letterSpacing: '1px', fontSize: '9px' },
  cachedBadge: {
    ...mono,
    fontSize: '9px',
    letterSpacing: '2px',
    color: 'var(--accent-yellow)',
    border: '1px solid rgba(255, 204, 0, 0.4)',
    padding: '2px 6px',
  },
  tiles: { marginBottom: '24px' },
  tile: { display: 'flex', flexDirection: 'column', gap: '6px', padding: '14px', background: 'var(--bg-secondary)', minWidth: 0 },
  tileLabel: label,
  tileValue: { ...mono, fontSize: '14px', fontWeight: 700, letterSpacing: '1px', overflowWrap: 'anywhere' },
  tileSub: { ...mono, fontSize: '10px', color: 'var(--text-muted)' },
  meter: { display: 'block', height: '3px', background: 'var(--border)', overflow: 'hidden' },
  meterFill: { display: 'block', height: '100%' },
  section: { marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid var(--border)' },
  sectionLabel: { ...label, letterSpacing: '3px', fontWeight: 400, marginBottom: '8px' },
  sectionContent: { fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.75 },
  lead: { fontSize: '14px', color: 'var(--text-primary)' },
  divided: { marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid var(--border)' },
  listSection: { display: 'flex', flexDirection: 'column', gap: '8px', minWidth: 0 },
  list: { listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px' },
  listItem: { display: 'flex', alignItems: 'flex-start', gap: '8px' },
  listText: { fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6, minWidth: 0 },
  none: { fontSize: '12px', color: 'var(--text-muted)' },
  details: { marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid var(--border)' },
  summary: { ...label, letterSpacing: '3px', cursor: 'pointer' },
  sourceList: { listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '12px' },
  sourceItem: { display: 'flex', gap: '10px', fontSize: '11px', lineHeight: 1.5, alignItems: 'baseline' },
  sourceId: { ...mono, fontSize: '9px', color: 'var(--accent-blue)', minWidth: '24px' },
  sourceLink: { color: 'var(--text-secondary)', textDecoration: 'underline', textDecorationColor: 'var(--border-bright)', overflowWrap: 'anywhere' },
  sourceLabel: { color: 'var(--text-secondary)', overflowWrap: 'anywhere' },
  sourceDate: { ...mono, fontSize: '9px', color: 'var(--text-muted)' },
  meta: { display: 'flex', flexDirection: 'column', gap: '14px' },
  metaItem: { display: 'flex', flexDirection: 'column', gap: '5px', padding: '12px 14px', background: 'var(--bg-primary)', minWidth: 0 },
  metaValue: { ...mono, fontSize: '12px', fontWeight: 700, overflowWrap: 'anywhere' },
  metaSub: { ...mono, fontSize: '9px', color: 'var(--text-muted)', lineHeight: 1.4, overflowWrap: 'anywhere' },
  metaBar: { display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' },
  cachedPill: { ...mono, fontSize: '9px', letterSpacing: '2px', color: 'var(--accent-yellow)' },
  freshPill: { ...mono, fontSize: '9px', letterSpacing: '2px', color: 'var(--accent-green)' },
  reportId: { ...mono, fontSize: '9px', letterSpacing: '2px', color: 'var(--text-muted)' },
  unavailable: { display: 'flex', flexDirection: 'column', gap: '8px' },
  unavailableLabel: label,
  unavailableList: { listStyle: 'none', display: 'flex', flexWrap: 'wrap', gap: '6px' },
  unavailableItem: {
    ...mono,
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '10px',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    padding: '4px 8px',
    cursor: 'help',
  },
}
