import { describe, expect, it } from 'vitest'
import {
  SOURCES,
  analysisStreamReducer as reduce,
  createInitialState,
  progressMessage,
  sourceList,
  summarizeSources,
} from '../analysisStream'

const source = (name, status, extra = {}) => ({ type: 'source', payload: { type: 'source', name, status, ...extra } })

describe('analysis stream reducer', () => {
  it('starts with all 13 sources pending, in display order', () => {
    const state = createInitialState()
    expect(state.phase).toBe('connecting')
    expect(sourceList(state).map((s) => s.name)).toEqual(SOURCES.map((s) => s.name))
    expect(SOURCES).toHaveLength(13)
    expect(summarizeSources(state)).toMatchObject({ total: 13, settled: 0, pending: 13 })
  })

  it('records final status, latency and detail for a source', () => {
    let state = createInitialState()
    state = reduce(state, source('profile', 'pending', { label: 'Company profile' }))
    state = reduce(state, source('profile', 'ok', { ms: 412 }))
    state = reduce(state, source('insider', 'error', { ms: 3001, detail: 'SEC request timed out' }))
    state = reduce(state, source('transcript', 'skipped', { detail: 'No API key' }))

    expect(state.phase).toBe('running')
    expect(state.sources.profile).toMatchObject({ status: 'ok', ms: 412, label: 'Company profile' })
    expect(state.sources.insider).toMatchObject({ status: 'error', detail: 'SEC request timed out' })
    expect(summarizeSources(state)).toMatchObject({ settled: 3, ok: 1, error: 1, skipped: 1, pending: 10 })
  })

  it('never regresses a settled source back to pending', () => {
    let state = reduce(createInitialState(), source('news', 'empty', { ms: 800 }))
    state = reduce(state, source('news', 'pending'))
    expect(state.sources.news).toMatchObject({ status: 'empty', ms: 800 })
  })

  it('appends sources the frontend does not know yet', () => {
    const state = reduce(createInitialState(), source('options_flow', 'ok', { label: 'Options flow', ms: 90 }))
    expect(state.order.at(-1)).toBe('options_flow')
    expect(summarizeSources(state).total).toBe(14)
  })

  it('treats an unknown status as an error', () => {
    const state = reduce(createInitialState(), source('price', 'weird'))
    expect(state.sources.price.status).toBe('error')
  })

  it('tracks the current stage and message', () => {
    const state = reduce(createInitialState(), {
      type: 'stage',
      payload: { stage: 'retrieval', message: 'Retrieving evidence by topic' },
    })
    expect(state).toMatchObject({ phase: 'running', stage: 'retrieval', message: 'Retrieving evidence by topic' })
  })

  it('finishes with a report and ignores later noise', () => {
    let state = reduce(createInitialState(), { type: 'report', payload: { data: { ticker: 'ACME' } } })
    expect(state).toMatchObject({ phase: 'done', response: { ticker: 'ACME' } })

    const after = reduce(state, { type: 'connection_lost', detail: 'closed' })
    expect(after).toBe(state)
    expect(reduce(state, source('price', 'ok'))).toBe(state)
  })

  it('surfaces a server error event', () => {
    const state = reduce(createInitialState(), {
      type: 'error',
      payload: { type: 'error', status: 502, error: 'llm_error', detail: 'Claude is overloaded', source: 'Anthropic' },
    })
    expect(state.phase).toBe('error')
    expect(state.error).toEqual({ status: 502, code: 'llm_error', detail: 'Claude is overloaded', source: 'Anthropic' })
  })

  it('turns a dropped connection into an error only before a final event', () => {
    const state = reduce(createInitialState(), { type: 'connection_lost', detail: 'Lost connection' })
    expect(state.error).toMatchObject({ code: 'connection_lost', detail: 'Lost connection' })
  })

  it('restart resets progress, bumps the run id and remembers refresh', () => {
    let state = reduce(createInitialState(), source('profile', 'ok'))
    state = reduce(state, { type: 'error', payload: { detail: 'x' } })
    const restarted = reduce(state, { type: 'restart', refresh: true })
    expect(restarted).toMatchObject({ runId: 1, refresh: true, phase: 'connecting', error: null, response: null })
    expect(restarted.sources.profile.status).toBe('pending')
  })

  it('follows Claude thinking, then writing with a character count', () => {
    let state = reduce(createInitialState(), { type: 'stage', payload: { stage: 'llm', message: 'Writing the report with claude' } })
    expect(progressMessage(state)).toBe('Writing the report with claude')

    state = reduce(state, { type: 'llm', payload: { type: 'llm', phase: 'thinking' } })
    expect(progressMessage(state)).toBe('Claude is reasoning over the evidence…')

    state = reduce(state, { type: 'llm', payload: { type: 'llm', phase: 'writing', chars: 1234 } })
    expect(progressMessage(state)).toBe('Writing report · 1.2k chars')
    state = reduce(state, { type: 'llm', payload: { type: 'llm', phase: 'writing', chars: 640 } })
    expect(progressMessage(state)).toBe('Writing report · 640 chars')
  })

  it('ignores llm events with an unknown phase or after the stream finished', () => {
    const state = reduce(createInitialState(), { type: 'llm', payload: { phase: 'dreaming' } })
    expect(state.llm).toBeNull()
    const done = reduce(state, { type: 'report', payload: { data: {} } })
    expect(reduce(done, { type: 'llm', payload: { phase: 'writing', chars: 10 } })).toBe(done)
    expect(reduce(done, { type: 'mystery', payload: {} })).toBe(done)
  })
})
