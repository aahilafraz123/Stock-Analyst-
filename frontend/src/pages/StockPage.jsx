import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCompetitors, getErrorDetail, getReportById, getSnapshot } from '../services/api'
import { useAnalysisStream } from '../hooks/useAnalysisStream'
import { useRequest } from '../hooks/useRequest'
import AnalysisPanel from '../components/AnalysisPanel'
import AskFilings from '../components/AskFilings'
import CompetitorTable from '../components/CompetitorTable'
import ErrorNotice from '../components/ErrorNotice'
import Loader from '../components/Loader'
import OverviewCard from '../components/OverviewCard'
import PriceChart from '../components/PriceChart'
import RatiosPanel from '../components/RatiosPanel'
import ReportHistory from '../components/ReportHistory'
import RiskDiff from '../components/RiskDiff'

export default function StockPage() {
  const { ticker = '' } = useParams()
  const symbol = ticker.trim().toUpperCase()
  // Remount per ticker: every request, the analysis stream and all panel state
  // start fresh, so nothing (an error, a stale report) carries over.
  return <StockView key={symbol} ticker={symbol} />
}

function StockView({ ticker }) {
  // Market data, peers and the AI analysis load independently: one failing
  // never hides the others.
  const snapshot = useRequest(ticker, (signal) => getSnapshot(ticker, { signal }))
  const competitors = useRequest(ticker, (signal) => getCompetitors(ticker, { signal }))
  const [stream, restartAnalysis] = useAnalysisStream(ticker)

  const [archivedId, setArchivedId] = useState(null)
  const liveReportId = stream.response?.meta?.reportId ?? null
  const showArchived = archivedId != null && archivedId !== liveReportId
  const archived = useRequest(showArchived ? `report:${archivedId}` : null, (signal) =>
    getReportById(archivedId, { signal }),
  )

  const profile = snapshot.data?.profile
  const restart = (options) => {
    setArchivedId(null)
    restartAnalysis(options)
  }

  return (
    <div className="page">
      <header className="topbar">
        <Link to="/" className="btn">
          ← TERMINAL
        </Link>
        <h1 className="topbar__ticker">{ticker}</h1>
        <span className="topbar__name">{profile?.companyName}</span>
        <span className="topbar__spacer" />
        <Link to="/track-record" className="btn">
          TRACK RECORD →
        </Link>
      </header>

      {/* Slot order: desktop keeps two columns; under 960px the columns dissolve and
          the slots line up as overview, chart, analysis, Q&A, risk diff, history, peers, ratios. */}
      <main className="stock-grid">
        <div className="stock-col">
          <Slot order={1}>
            {snapshot.loading && <Loader label="LOADING MARKET DATA" sub="Profile · Ratios · Analysts · Price" />}
            {snapshot.error && (
              <div className="panel">
                <ErrorNotice
                  title={`MARKET DATA UNAVAILABLE FOR ${ticker}`}
                  detail={getErrorDetail(snapshot.error)}
                  onRetry={snapshot.reload}
                />
              </div>
            )}
            {snapshot.data && <OverviewCard profile={profile} price={snapshot.data.price} />}
          </Slot>
          {snapshot.data && (
            <Slot order={2}>
              <PriceChart ticker={ticker} currentPrice={profile?.currentPrice} />
            </Slot>
          )}
          <Slot order={6}>
            <ReportHistory
              ticker={ticker}
              refreshKey={liveReportId}
              activeId={showArchived ? archivedId : liveReportId}
              onSelect={setArchivedId}
            />
          </Slot>
          {snapshot.data && (
            <Slot order={8}>
              <RatiosPanel ratios={snapshot.data.ratios} />
            </Slot>
          )}
        </div>

        <div className="stock-col">
          <Slot order={3}>
            <AnalysisPanel
              ticker={ticker}
              stream={stream}
              onRestart={restart}
              archived={showArchived ? { id: archivedId, ...archived } : null}
              onCloseArchived={() => setArchivedId(null)}
            />
          </Slot>
          <Slot order={4}>
            <AskFilings ticker={ticker} />
          </Slot>
          <Slot order={5}>
            <RiskDiff ticker={ticker} />
          </Slot>
          <Slot order={7}>
            <CompetitorTable
              ticker={ticker}
              competitors={competitors.data}
              loading={competitors.loading}
              error={competitors.error}
              onRetry={competitors.reload}
            />
          </Slot>
        </div>
      </main>
    </div>
  )
}

function Slot({ order, children }) {
  return (
    <div className="stock-slot" style={{ order }}>
      {children}
    </div>
  )
}
