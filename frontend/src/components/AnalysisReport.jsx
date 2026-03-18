const signalColor = (s) => ({
  BULLISH: 'var(--accent-green)',
  BEARISH: 'var(--accent-red)',
  NEUTRAL: 'var(--accent-yellow)',
}[s] || 'var(--text-secondary)')

const recColor = (r) => ({
  BUY: 'var(--accent-green)',
  SELL: 'var(--accent-red)',
  HOLD: 'var(--accent-yellow)',
}[r] || 'var(--text-secondary)')

export default function AnalysisReport({ analysis }) {
  if (!analysis) return null
  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>AI ANALYSIS REPORT</div>

      <div style={styles.topRow}>
        <div style={styles.signal}>
          <span style={styles.signalLabel}>SIGNAL</span>
          <span style={{ ...styles.signalValue, color: signalColor(analysis.overallSignal) }}>
            {analysis.overallSignal}
          </span>
        </div>
        <div style={styles.signal}>
          <span style={styles.signalLabel}>RECOMMENDATION</span>
          <span style={{ ...styles.signalValue, color: recColor(analysis.recommendation) }}>
            {analysis.recommendation}
          </span>
        </div>
        <div style={styles.signal}>
          <span style={styles.signalLabel}>CONFIDENCE</span>
          <span style={styles.signalValue}>{analysis.confidenceScore}/100</span>
        </div>
        <div style={styles.signal}>
          <span style={styles.signalLabel}>VALUATION</span>
          <span style={styles.signalValue}>{analysis.valuation?.assessment}</span>
        </div>
        <div style={styles.signal}>
          <span style={styles.signalLabel}>FINANCIAL HEALTH</span>
          <span style={{ ...styles.signalValue, color: analysis.financialHealth?.assessment === 'STRONG' ? 'var(--accent-green)' : analysis.financialHealth?.assessment === 'WEAK' ? 'var(--accent-red)' : 'var(--accent-yellow)' }}>
            {analysis.financialHealth?.assessment}
          </span>
        </div>
        <div style={styles.signal}>
          <span style={styles.signalLabel}>ANALYST TARGET</span>
          <span style={{ ...styles.signalValue, color: 'var(--accent-green)' }}>
            {analysis.analystConsensus
              ? analysis.analystConsensus.match(/\$[\d,.]+/)?.[0] || '—'
              : '—'}
          </span>
        </div>
      </div>

      <Section label="EXECUTIVE SUMMARY" content={analysis.summary} />
      <Section label="PRICE CONTEXT & MOMENTUM" content={analysis.priceContext} />
      <Section label="WALL STREET CONSENSUS" content={analysis.analystConsensus} />
      <Section label="RECOMMENDATION REASONING" content={analysis.recommendationReasoning} />
      <Section label="VALUATION" content={analysis.valuation?.reasoning} />
      <Section label="COMPETITIVE POSITION" content={analysis.competitivePosition} />
      <Section label="RECENT NEWS IMPACT" content={analysis.recentNewsImpact} />

      <div style={styles.listsRow}>
        <ListSection label="STRENGTHS" items={analysis.strengths} color="var(--accent-green)" />
        <ListSection label="RISKS" items={analysis.risks} color="var(--accent-red)" />
      </div>

      <div style={styles.healthRow}>
        <span style={styles.healthLabel}>FINANCIAL HEALTH DETAIL</span>
        <span style={styles.healthReason}>{analysis.financialHealth?.reasoning}</span>
      </div>
    </div>
  )
}

function Section({ label, content }) {
  if (!content) return null
  return (
    <div style={styles.section}>
      <div style={styles.sectionLabel}>{label}</div>
      <p style={styles.sectionContent}>{content}</p>
    </div>
  )
}

function ListSection({ label, items, color }) {
  return (
    <div style={styles.listSection}>
      <div style={styles.sectionLabel}>{label}</div>
      {(items || []).map((item, i) => (
        <div key={i} style={styles.listItem}>
          <span style={{ color, marginRight: '8px' }}>▸</span>
          <span style={styles.listText}>{item}</span>
        </div>
      ))}
    </div>
  )
}

const styles = {
  card: { background: 'var(--bg-card)', padding: '28px' },
  cardHeader: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '4px',
    color: 'var(--text-muted)',
    marginBottom: '20px',
  },
  topRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '1px',
    background: 'var(--border)',
    border: '1px solid var(--border)',
    marginBottom: '24px',
  },
  signal: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    padding: '14px',
    background: 'var(--bg-secondary)',
  },
  signalLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
  },
  signalValue: {
    fontFamily: 'var(--font-mono)',
    fontSize: '14px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    letterSpacing: '1px',
  },
  section: {
    marginBottom: '20px',
    paddingBottom: '20px',
    borderBottom: '1px solid var(--border)',
  },
  sectionLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    color: 'var(--text-muted)',
    letterSpacing: '3px',
    marginBottom: '8px',
  },
  sectionContent: {
    fontFamily: 'var(--font-sans)',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    lineHeight: 1.7,
  },
  listsRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '24px',
    marginBottom: '20px',
    paddingBottom: '20px',
    borderBottom: '1px solid var(--border)',
  },
  listSection: { display: 'flex', flexDirection: 'column', gap: '8px' },
  listItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '4px',
  },
  listText: {
    fontFamily: 'var(--font-sans)',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    lineHeight: 1.5,
  },
  healthRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  healthLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    color: 'var(--text-muted)',
    letterSpacing: '3px',
    marginBottom: '4px',
  },
  healthReason: {
    fontFamily: 'var(--font-sans)',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
  },
}
