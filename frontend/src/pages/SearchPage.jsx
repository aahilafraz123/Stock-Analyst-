import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const POPULAR = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'JPM']

export default function SearchPage() {
  const [ticker, setTicker] = useState('')
  const navigate = useNavigate()

  const handleSearch = (t) => {
    const val = (t || ticker).toUpperCase().trim()
    if (val) navigate(`/stock/${encodeURIComponent(val)}`)
  }

  return (
    <main className="search-page">
      <div className="search-page__grid" aria-hidden="true" />
      <div className="search-page__center">
        <div style={styles.badge}>EQUITY RESEARCH TERMINAL</div>
        <h1 style={styles.title}>STOCK<span style={styles.accent}>ANALYZER</span></h1>
        <p style={styles.subtitle}>
          Cited AI research reports · Q&amp;A over SEC filings · Risk-factor diffs · A public track record
        </p>

        <form
          style={styles.searchBox}
          onSubmit={(e) => {
            e.preventDefault()
            handleSearch()
          }}
        >
          <span style={styles.searchIcon} aria-hidden="true">$</span>
          <input
            style={styles.input}
            placeholder="Enter ticker symbol..."
            aria-label="Ticker symbol"
            value={ticker}
            maxLength={12}
            onChange={e => setTicker(e.target.value.toUpperCase())}
            autoFocus
          />
          <button type="submit" style={styles.searchBtn}>
            ANALYZE →
          </button>
        </form>

        <div style={styles.popularRow}>
          <span style={styles.popularLabel}>POPULAR:</span>
          {POPULAR.map(t => (
            <button key={t} type="button" className="btn" style={styles.chip} onClick={() => handleSearch(t)}>
              {t}
            </button>
          ))}
        </div>

        <Link to="/track-record" className="btn" style={styles.trackLink}>
          VIEW THE TRACK RECORD →
        </Link>
      </div>

      <div className="search-page__features">
        <span style={styles.footerItem}>● LIVE MARKET DATA</span>
        <span style={styles.footerItem}>● SEC EDGAR</span>
        <span style={styles.footerItem}>● RAG OVER FILINGS</span>
        <span style={styles.footerItem}>● CITED AI ANALYSIS</span>
      </div>
    </main>
  )
}

const styles = {
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
    fontSize: 'clamp(34px, 9vw, 80px)',
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
    alignItems: 'stretch',
    width: '100%',
    border: '1px solid var(--border-bright)',
    background: 'var(--bg-card)',
    marginTop: '16px',
    transition: 'border-color 0.2s',
  },
  searchIcon: {
    display: 'flex',
    alignItems: 'center',
    fontFamily: 'var(--font-mono)',
    fontSize: '20px',
    color: 'var(--accent-green)',
    padding: '0 16px',
  },
  input: {
    flex: 1,
    minWidth: 0,
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
    padding: '18px clamp(14px, 4vw, 28px)',
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
    padding: '6px 14px',
    fontSize: '12px',
    letterSpacing: '1px',
  },
  trackLink: {
    color: 'var(--accent-green)',
    borderColor: 'rgba(0, 255, 136, 0.4)',
  },
  footerItem: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-muted)',
    letterSpacing: '2px',
  },
}