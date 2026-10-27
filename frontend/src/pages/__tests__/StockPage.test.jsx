import { act, render, screen, within } from '@testing-library/react'
import { useEffect } from 'react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import StockPage from '../StockPage'
import { FakeEventSource } from '../../test/FakeEventSource'
import { analysisResponse, apiError, snapshot } from '../../test/fixtures'
import { getCompetitors, getSnapshot } from '../../services/api'

vi.mock('../../services/api', async (importOriginal) => ({
  ...(await importOriginal()),
  getSnapshot: vi.fn(),
  getCompetitors: vi.fn(),
  getHistory: vi.fn(() => Promise.resolve([])),
  getReports: vi.fn(() => Promise.resolve([])),
  getRagDocuments: vi.fn(() => Promise.resolve({ documents: [] })),
  getReportById: vi.fn(),
}))

// Lets a test navigate the router the way a link click would.
const router = { navigate: null }
function NavigationProbe() {
  const navigate = useNavigate()
  useEffect(() => {
    router.navigate = navigate
  }, [navigate])
  return null
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/stock/:ticker" element={<StockPage />} />
      </Routes>
      <NavigationProbe />
    </MemoryRouter>,
  )
}

const streamFor = (ticker) => FakeEventSource.instances.filter((es) => es.url.includes(`/analysis/${ticker}/stream`))

describe('StockPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    FakeEventSource.reset()
    vi.stubGlobal('EventSource', FakeEventSource)
    vi.mocked(getCompetitors).mockResolvedValue({ ACME: { name: 'Acme Robotics Inc.', peRatio: 30 } })
    vi.mocked(getSnapshot).mockImplementation((ticker) =>
      ticker === 'BAD'
        ? Promise.reject(apiError(404, 'No market data found for BAD', 'not_found'))
        : Promise.resolve(snapshot),
    )
  })

  afterEach(() => vi.unstubAllGlobals())

  it('clears a failed ticker when navigating to another one', async () => {
    renderAt('/stock/BAD')
    expect(await screen.findByText('No market data found for BAD')).toBeInTheDocument()
    const badStreams = streamFor('BAD')
    expect(badStreams.length).toBeGreaterThan(0)

    await act(async () => router.navigate('/stock/acme'))

    expect(await screen.findByRole('heading', { name: 'ACME' })).toBeInTheDocument()
    expect(await screen.findAllByText('Acme Robotics Inc.')).not.toHaveLength(0)
    expect(screen.queryByText('No market data found for BAD')).not.toBeInTheDocument()
    expect(screen.queryByText(/MARKET DATA UNAVAILABLE/)).not.toBeInTheDocument()

    // The old ticker's stream is closed and requests were made with an AbortSignal.
    expect(badStreams.every((es) => es.closed)).toBe(true)
    expect(streamFor('ACME').at(-1).closed).toBe(false)
    expect(getSnapshot).toHaveBeenLastCalledWith('ACME', expect.objectContaining({ signal: expect.any(AbortSignal) }))
  })

  it('keeps the analysis independent of a market-data failure', async () => {
    renderAt('/stock/BAD')
    expect(await screen.findByText('No market data found for BAD')).toBeInTheDocument()

    act(() => {
      const es = streamFor('BAD').at(-1)
      es.emit('stage', { type: 'stage', stage: 'sources', message: 'Fetching data sources in parallel' })
      es.emit('source', { type: 'source', name: 'profile', label: 'Company profile', status: 'ok', ms: 410 })
    })
    expect(screen.getByText('Fetching data sources in parallel')).toBeInTheDocument()
    expect(screen.getByRole('listitem', { name: /company profile: ok, 410ms/i })).toBeInTheDocument()

    act(() => {
      const es = streamFor('BAD').at(-1)
      es.emit('stage', { type: 'stage', stage: 'llm', message: 'Writing the report' })
      es.emit('llm', { type: 'llm', phase: 'thinking' })
      es.emit('options_flow', { type: 'options_flow' }) // unknown events are ignored
    })
    expect(screen.getByText('Claude is reasoning over the evidence…')).toBeInTheDocument()
    act(() => streamFor('BAD').at(-1).emit('llm', { type: 'llm', phase: 'writing', chars: 1234 }))
    expect(screen.getByText('Writing report · 1.2k chars')).toBeInTheDocument()

    act(() => streamFor('BAD').at(-1).emit('report', { type: 'report', data: analysisResponse }))
    expect(screen.getByText('AI ANALYSIS REPORT')).toBeInTheDocument()
    expect(screen.getByText(/fifth straight quarter/)).toBeInTheDocument()
    expect(screen.getByText('No market data found for BAD')).toBeInTheDocument()
  })

  it('shows a failed analysis with the backend message and retries it', async () => {
    const user = userEvent.setup()
    renderAt('/stock/ACME')
    expect(await screen.findAllByText('Acme Robotics Inc.')).not.toHaveLength(0)

    const first = streamFor('ACME').at(-1)
    act(() =>
      first.emit('error', { type: 'error', status: 502, error: 'llm_error', detail: 'Claude API is overloaded', source: 'Anthropic' }),
    )
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('AI ANALYSIS FAILED')
    expect(alert).toHaveTextContent('Claude API is overloaded')
    expect(first.closed).toBe(true)

    await user.click(within(alert).getByRole('button', { name: /retry/i }))
    const second = streamFor('ACME').at(-1)
    expect(second).not.toBe(first)
    expect(second.closed).toBe(false)
    expect(screen.queryByText('Claude API is overloaded')).not.toBeInTheDocument()
    expect(screen.getByText(/RUNNING AI ANALYSIS · ACME/)).toBeInTheDocument()
  })

  it('treats a dropped connection as a failure and regenerates with refresh=true', async () => {
    const user = userEvent.setup()
    renderAt('/stock/ACME')
    act(() => streamFor('ACME').at(-1).fail())
    expect(screen.getByRole('alert')).toHaveTextContent(/lost connection/i)

    await user.click(screen.getByRole('button', { name: /retry/i }))
    act(() => streamFor('ACME').at(-1).emit('report', { type: 'report', data: analysisResponse }))
    await user.click(screen.getByRole('button', { name: /regenerate/i }))
    expect(streamFor('ACME').at(-1).url).toMatch(/refresh=true$/)
  })
})
