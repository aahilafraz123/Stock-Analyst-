import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const POPULAR = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'JPM']

export default function SearchPage() {
  const [ticker, setTicker] = useState('')
  const navigate = useNavigate()

  const handleSearch = (t) => {
    const val = (t || ticker).toUpperCase().trim()
    if (val) navigate(`/stock/${val}`)
  }

  return (
    <div style={styles.page}>
      <div style={styles.grid} />
      <div style={styles.center}>
        <div style={styles.badge}>EQUITY RESEARCH TERMINAL</div>
        <h1 style={styles.title}>STOCK<span style={styles.accent}>ANALYZER</span></h1>
        <p style={styles.subtitle}>AI-powered fundamental analysis · Live financial data · SEC filings</p>

        <div style={styles.searchBox}>
          <span style={styles.searchIcon}>$</span>
          <input
            style={styles.input}
            placeholder="Enter ticker symbol..."
            value={ticker}
            onChange={e => setTicker(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            autoFocus
          />
          <button style={styles.searchBtn} onClick={() => handleSearch()}>
            ANALYZE →
          </button>
        </div>

        <div style={styles.popularRow}>
          <span style={styles.popularLabel}>POPULAR:</span>
          {POPULAR.map(t => (
            <button key={t} style={styles.chip} onClick={() => handleSearch(t)}>
              {t}
            </button>
          ))}
        </div>
      </div>

      <div style={styles.footer}>
        <span style={styles.footerItem}>● LIVE DATA</span>
        <span style={styles.footerItem}>● SEC EDGAR</span>
        <span style={styles.footerItem}>● AI ANALYSIS</span>
        <span style={styles.footerItem}>● REAL-TIME NEWS</span>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    overflow: 'hidden',
    background: 'var(--bg-primary)',
  },
  grid: {
    position: 'absolute',
    inset: 0,
    backgroundImage: `
      linear-gradient(var(--border) 1px, transparent 1px),
      linear-gradient(90deg, var(--border) 1px, transparent 1px)
    `,
    backgroundSize: '60px 60px',
    opacity: 0.4,
    pointerEvents: 'none',
  },
  center: {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '24px',
    padding: '40px',
    maxWidth: '700px',
    width: '100%',
  },
  badge: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--accent-green)',
    letterSpacing: '4px',
    border: '1px solid var(--accent-green)',
    padding: '4px 12px',
    opacity: 0.8,
  },
  title: {
    fontFamily: 'var(--font-sans)',
    fontSize: 'clamp(48px, 8vw, 80px)',
    fontWeight: 800,
    letterSpacing: '-2px',
    color: 'var(--text-primary)',
    lineHeight: 1,
  },
  accent: {
    color: 'var(--accent-green)',
  },
  subtitle: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    letterSpacing: '1px',
    textAlign: 'center',
  },
  searchBox: {
    display: 'flex',
    alignItems: 'center',
    width: '100%',
    border: '1px solid var(--border-bright)',
    background: 'var(--bg-card)',
    marginTop: '16px',
    transition: 'border-color 0.2s',
  },
  searchIcon: {
    fontFamily: 'var(--font-mono)',
    fontSize: '20px',
    color: 'var(--accent-green)',
    padding: '0 16px',
  },
  input: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
    fontSize: '20px',
    padding: '18px 0',
    letterSpacing: '2px',
  },
  searchBtn: {
    background: 'var(--accent-green)',
    color: 'var(--bg-primary)',
    border: 'none',
    padding: '18px 28px',
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    fontWeight: 700,
    letterSpacing: '2px',
    cursor: 'pointer',
  },
  popularRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  popularLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
  },
  chip: {
    background: 'transparent',
    border: '1px solid var(--border-bright)',
    color: 'var(--text-secondary)',
    padding: '6px 14px',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    cursor: 'pointer',
    letterSpacing: '1px',
    transition: 'all 0.15s',
  },
  footer: {
    position: 'absolute',
    bottom: '24px',
    display: 'flex',
    gap: '32px',
  },
  footerItem: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
  },
}