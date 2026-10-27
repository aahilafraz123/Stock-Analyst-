import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AskFilings from '../AskFilings'
import { apiError, askResponse } from '../../test/fixtures'
import { askFilings, getRagDocuments } from '../../services/api'

vi.mock('../../services/api', async (importOriginal) => ({
  ...(await importOriginal()),
  getRagDocuments: vi.fn(),
  askFilings: vi.fn(),
}))

const deferred = () => {
  let resolve, reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('AskFilings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getRagDocuments).mockResolvedValue({ ticker: 'ACME', retrieval: 'hybrid', documents: [] })
  })

  it('says the first question indexes the filings, then renders the cited answer', async () => {
    const user = userEvent.setup()
    const pending = deferred()
    vi.mocked(askFilings).mockReturnValue(pending.promise)
    render(<AskFilings ticker="ACME" />)

    expect(await screen.findByText('NOT INDEXED YET')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /revenue and margins/i }))
    expect(askFilings).toHaveBeenCalledWith('ACME', expect.stringMatching(/revenue and margins/), expect.objectContaining({ signal: expect.any(AbortSignal) }))
    expect(screen.getByRole('status')).toHaveTextContent(/indexing ACME's filings .* for the first time/i)

    pending.resolve(askResponse)
    const answer = await screen.findByTestId('answer-text')
    expect(answer).toHaveTextContent('Software subscriptions reached 31% of revenue1, helped by higher attach rates2.')

    // One marker per cited source (the duplicate citation collapses), linked to the numbered list.
    const markers = within(answer).getAllByRole('link')
    expect(markers.map((m) => m.textContent)).toEqual(['1', '2'])
    const list = screen.getByRole('list', { name: 'Answer sources' })
    const items = within(list).getAllByRole('listitem')
    expect(markers[0].getAttribute('href')).toBe(`#${items[0].id}`)
    expect(markers[1].getAttribute('href')).toBe(`#${items[1].id}`)
    expect(markers[0]).toHaveAttribute('title', 'Software subscriptions grew to 31% of revenue.')

    expect(items[0]).toHaveTextContent('ACME 10-K (FY2026) · MD&A')
    expect(items[0]).toHaveTextContent('2026-08-30')
    expect(within(items[0]).getByRole('link', { name: /open filing/i })).toHaveAttribute('href', 'https://example.com/acme-10k')
    expect(within(items[1]).queryByRole('link')).not.toBeInTheDocument()

    expect(screen.getByTestId('indexed-count')).toHaveTextContent('5 DOCUMENTS INDEXED')
  })

  it('uses the regular loading copy once documents are indexed', async () => {
    vi.mocked(getRagDocuments).mockResolvedValue({ retrieval: 'bm25', documents: [{ doc_id: 'a' }, { doc_id: 'b' }] })
    vi.mocked(askFilings).mockReturnValue(new Promise(() => {}))
    const user = userEvent.setup()
    render(<AskFilings ticker="ACME" />)
    expect(await screen.findByText('2 DOCUMENTS INDEXED · BM25')).toBeInTheDocument()

    await user.type(screen.getByRole('textbox'), 'What is the backlog?{Enter}')
    expect(screen.getByRole('status')).toHaveTextContent(/drafting a cited answer/i)
  })

  it("shows the backend's error message with a retry", async () => {
    vi.mocked(askFilings).mockRejectedValueOnce(apiError(502, 'SEC EDGAR is unavailable')).mockResolvedValueOnce(askResponse)
    const user = userEvent.setup()
    render(<AskFilings ticker="ACME" />)

    await user.type(screen.getByRole('textbox'), 'What is the backlog?{Enter}')
    expect(await screen.findByRole('alert')).toHaveTextContent('SEC EDGAR is unavailable')

    await user.click(screen.getByRole('button', { name: /retry/i }))
    expect(await screen.findByTestId('answer-text')).toBeInTheDocument()
    expect(askFilings).toHaveBeenCalledTimes(2)
  })
})
