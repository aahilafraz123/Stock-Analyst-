import { BrowserRouter, Routes, Route } from 'react-router-dom'
import SearchPage from './pages/SearchPage'
import StockPage from './pages/StockPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/stock/:ticker" element={<StockPage />} />
      </Routes>
    </BrowserRouter>
  )
}