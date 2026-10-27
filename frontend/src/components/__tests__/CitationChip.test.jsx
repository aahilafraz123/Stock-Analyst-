import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import CitationChip, { Citations } from '../CitationChip'

const filing = {
  id: 'F3',
  kind: '10-K',
  label: 'ACME 10-K (FY2026) · Risk Factors',
  url: 'https://example.com/acme-10k#risk',
  date: '2026-08-30',
  excerpt: 'Two customers accounted for 41% of revenue.',
}

describe('CitationChip', () => {
  it('previews the source on hover and hides it again on leave', async () => {
    const user = userEvent.setup()
    render(<CitationChip id="F3" source={filing} />)
    const chip = screen.getByRole('button', { name: /source f3/i })
    expect(chip).toHaveTextContent('[F3]')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await user.hover(chip)
    const popover = screen.getByRole('dialog', { name: 'Source F3' })
    expect(popover).toHaveTextContent(filing.label)
    expect(popover).toHaveTextContent('2026-08-30')
    expect(popover).toHaveTextContent('Two customers accounted for 41% of revenue.')
    expect(within(popover).getByRole('link', { name: /open source/i })).toHaveAttribute('href', filing.url)
    expect(chip).toHaveAttribute('aria-expanded', 'true')

    await user.unhover(chip)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('pins on click until Escape', async () => {
    const user = userEvent.setup()
    render(<CitationChip id="F3" source={filing} />)
    const chip = screen.getByRole('button', { name: /source f3/i })

    await user.click(chip)
    await user.unhover(chip)
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('closes a pinned popover on an outside click or a second click', async () => {
    const user = userEvent.setup()
    render(
      <div>
        <p>outside</p>
        <CitationChip id="F3" source={filing} />
      </div>,
    )
    const chip = screen.getByRole('button', { name: /source f3/i })
    await user.click(chip)
    fireEvent.pointerDown(screen.getByText('outside'))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await user.click(chip)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await user.click(chip)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('omits the link when the source has no url', async () => {
    const user = userEvent.setup()
    render(<CitationChip id="M1" source={{ id: 'M1', kind: 'market', label: 'Company fundamentals', url: null, date: null, excerpt: 'P/E 24' }} />)
    await user.click(screen.getByRole('button', { name: /source m1/i }))
    expect(screen.getByRole('dialog')).toHaveTextContent('Company fundamentals')
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('explains a citation whose source is missing', async () => {
    const user = userEvent.setup()
    render(<CitationChip id="X9" />)
    await user.click(screen.getByRole('button', { name: 'Source X9' }))
    expect(screen.getByRole('dialog')).toHaveTextContent(/not available/i)
  })
})

describe('Citations', () => {
  it('renders one chip per unique id', () => {
    render(<Citations ids={['F3', 'N2', 'F3']} sources={{ F3: filing }} />)
    expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual(['[F3]', '[N2]'])
  })
})
