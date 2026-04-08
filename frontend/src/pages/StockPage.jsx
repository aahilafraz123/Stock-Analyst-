import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getProfile, getRatios, getCompetitors, getAnalysis } from '../services/api'
import OverviewCard from '../components/OverviewCard'
import RatiosPanel from '../components/RatiosPanel'
import PriceChart from '../components/PriceChart'
import CompetitorTable from '../components/CompetitorTable'
import AnalysisReport from '../components/AnalysisReport'
import Loader from '../components/Loader'
export default function StockPage() {
  const { ticker } = useParams()
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [ratios, setRatios] = useState(null)
  const [competitors, setCompetitors] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loadingBase, setLoadingBase] = useState(true)
  const [loadingAnalysis, setLoadingAnalysis] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoadingBase(true)
    setLoadingAnalysis(true)
    setProfile(null)
    setRatios(null)
    setCompetitors(null)
    setAnalysis(null)

    // Stage 1 — load fast data first (profile, ratios, competitors)
    Promise.all([
      getProfile(ticker),
      getRatios(ticker),
      getCompetitors(ticker),
    ]).then(([p, r, c]) => {
      setProfile(p.data)
      setRatios(r.data)
      setCompetitors(c.data)
      setLoadingBase(false)
    }).catch(() => {
      setError('Failed to load data for ' + ticker)
      setLoadingBase(false)
      setLoadingAnalysis(false)
    })

    // Stage 2 — load AI analysis independently (takes longer)
    getAnalysis(ticker)
      .then(a => {
        setAnalysis(a.data)
        setLoadingAnalysis(false)
      })
      .catch(() => {
        setLoadingAnalysis(false)
      })

  }, [ticker])

  if (loadingBase) return <Loader ticker={ticker} />

  if (error) return (
    <div style={styles.errorPage}>
      <div style={styles.errorBox}>
        <div style={styles.errorCode}>ERROR</div>
        <div style={styles.errorMsg}>{error}</div>
        <button style={styles.backBtn} onClick={() => navigate('/')}>← BACK TO SEARCH</button>
      </div>
    </div>
  )

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <button style={styles.backBtn} onClick={() => navigate('/')}>← TERMINAL</button>
        <div style={styles.headerTicker}>{ticker}</div>
        <div style={styles.headerName}>{profile?.companyName}</div>
      </header>

      <div style={styles.grid}>
        <div style={styles.colLeft}>
          <OverviewCard profile={profile} ratios={ratios} />
          <PriceChart ticker={ticker} currentPrice={profile?.currentPrice} />
          <RatiosPanel ratios={ratios} />
        </div>
        <div style={styles.colRight}>
          {loadingAnalysis ? (
            <div style={styles.analysisLoading}>
              <div style={styles.analysisSpinner} />
              <div style={styles.analysisLoadingText}>RUNNING AI ANALYSIS...</div>
              <div style={styles.analysisLoadingSub}>Parsing 10-Q · Scanning news · Generating report</div>
            </div>
          ) : (
            <AnalysisReport analysis={analysis} />
          )}
          <CompetitorTable competitors={competitors} ticker={ticker} />
        </div>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight: '100vh',
    background: 'var(--bg-primary)',
    paddingBottom: '60px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
    padding: '20px 40px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-secondary)',
  },
  backBtn: {
    background: 'transparent',
    border: '1px solid var(--border-bright)',
    color: 'var(--text-secondary)',
    padding: '8px 16px',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    letterSpacing: '2px',
    cursor: 'pointer',
  },
  headerTicker: {
    fontFamily: 'var(--font-mono)',
    fontSize: '24px',
    fontWeight: 700,
    color: 'var(--accent-green)',
    letterSpacing: '3px',
  },
  headerName: {
    fontFamily: 'var(--font-sans)',
    fontSize: '14px',
    color: 'var(--text-secondary)',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1.4fr',
    gap: '1px',
    background: 'var(--border)',
    margin: '40px',
    border: '1px solid var(--border)',
  },
  colLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1px',
    background: 'var(--border)',
  },
  colRight: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1px',
    background: 'var(--border)',
  },
  analysisLoading: {
    background: 'var(--bg-card)',
    padding: '60px 28px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    minHeight: '300px',
  },
  analysisSpinner: {
    width: '32px',
    height: '32px',
    border: '2px solid var(--border-bright)',
    borderTop: '2px solid var(--accent-green)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  analysisLoadingText: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--accent-green)',
    letterSpacing: '4px',
  },
  analysisLoadingSub: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
    letterSpacing: '1px',
  },
  errorPage: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--bg-primary)',
  },
  errorBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
  },
  errorCode: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--accent-red)',
    letterSpacing: '4px',
  },
  errorMsg: {
    fontFamily: 'var(--font-sans)',
    fontSize: '18px',
    color: 'var(--text-secondary)',
  },
}