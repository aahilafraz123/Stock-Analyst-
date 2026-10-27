import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import AnalysisReport from '../AnalysisReport'
import { analysisResponse } from '../../test/fixtures'

describe('AnalysisReport', () => {
  it('takes the analyst target from metrics, not from the prose', () => {
    render(<AnalysisReport response={analysisResponse} />)
    const tile = screen.getByText('ANALYST TARGET').parentElement
    expect(tile).toHaveTextContent('$132.50')
    expect(tile).toHaveTextContent('+10.4%')
    expect(tile).toHaveTextContent('14 analysts')
    expect(tile).not.toHaveTextContent('$999')
  })

  it('puts citation chips after claims and renders the new sections', () => {
    render(<AnalysisReport response={analysisResponse} />)
    const summary = screen.getByText(/fifth straight quarter/).closest('p')
    expect(within(summary).getAllByRole('button').map((b) => b.textContent)).toEqual(['[F2]', '[T1]'])
    expect(screen.getByText('CATALYSTS')).toBeInTheDocument()
    expect(screen.getByText(/New mid-size robot ships/)).toBeInTheDocument()
    expect(screen.getByText('MANAGEMENT TONE')).toBeInTheDocument()
  })

  it('shows model, tokens, groundedness, cache state and unavailable sources', async () => {
    const onRegenerate = vi.fn()
    const user = userEvent.setup()
    render(<AnalysisReport response={analysisResponse} onRegenerate={onRegenerate} />)
    const footer = screen.getByLabelText('Report metadata')

    expect(footer).toHaveTextContent('claude-opus-5-5')
    expect(footer).toHaveTextContent('31,250 / 2,890')
    expect(footer).toHaveTextContent('41.0s')
    expect(footer).toHaveTextContent('HYBRID')
    expect(footer).toHaveTextContent('18')
    expect(footer).toHaveTextContent('95%')
    expect(footer).toHaveTextContent('19/20 claims cited')
    expect(footer).toHaveTextContent('CACHED REPORT')

    expect(footer).toHaveTextContent('UNAVAILABLE SOURCES (2)')
    expect(footer).toHaveTextContent('Insider trades')
    expect(footer).toHaveTextContent('Earnings call transcript')
    expect(footer).not.toHaveTextContent('News (14 days)')

    await user.click(within(footer).getByRole('button', { name: /regenerate/i }))
    expect(onRegenerate).toHaveBeenCalledTimes(1)
  })
})
