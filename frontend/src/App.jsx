import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import SearchPage from './pages/SearchPage'
import SiteFooter from './components/SiteFooter'
import Loader from './components/Loader'

// The stock page pulls in recharts; load it (and the track record) on demand.
const StockPage = lazy(() => import('./pages/StockPage'))
const TrackRecordPage = lazy(() => import('./pages/TrackRecordPage'))

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <div className="app-main">
          <Suspense fallback={<Loader label="LOADING" minHeight="60vh" />}>
            <Routes>
              <Route path="/" element={<SearchPage />} />
              <Route path="/stock/:ticker" element={<StockPage />} />
              <Route path="/track-record" element={<TrackRecordPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </div>
        <SiteFooter />
      </div>
    </BrowserRouter>
  )
}
