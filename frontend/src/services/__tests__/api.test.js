import { AxiosError, CanceledError } from 'axios'
import { describe, expect, it } from 'vitest'
import { API_URL, analysisStreamUrl, getErrorDetail, isAbortError } from '../api'
import { apiError } from '../../test/fixtures'

describe('getErrorDetail', () => {
  it("returns the backend's `detail` message", () => {
    expect(getErrorDetail(apiError(404, 'No data found for ticker ZZZZ', 'not_found'))).toBe(
      'No data found for ticker ZZZZ',
    )
  })

  it('joins FastAPI validation messages', () => {
    const err = apiError(422)
    err.response.data = { detail: [{ loc: ['body', 'question'], msg: 'String should have at least 3 characters' }, { msg: 'Field required' }] }
    expect(getErrorDetail(err)).toBe('String should have at least 3 characters; Field required')
  })

  it('falls back to the error code when there is no detail', () => {
    const err = apiError(503)
    err.response.data = { error: 'not_configured' }
    expect(getErrorDetail(err)).toBe('not configured')
  })

  it('ignores HTML error pages and reports the status', () => {
    const err = apiError(502)
    err.response.data = '<html><body>Bad Gateway</body></html>'
    expect(getErrorDetail(err)).toBe('Request failed with status 502.')
  })

  it('explains network failures with the configured API URL', () => {
    const err = new AxiosError('Network Error', 'ERR_NETWORK', undefined, {})
    expect(getErrorDetail(err)).toBe(`Cannot reach the API at ${API_URL}. Is the backend running?`)
  })

  it('explains timeouts', () => {
    const err = new AxiosError('timeout of 60000ms exceeded', 'ECONNABORTED', undefined, {})
    expect(getErrorDetail(err)).toMatch(/timed out/)
  })

  it('recognises cancellations and uses the fallback for empty input', () => {
    const cancelled = new CanceledError()
    expect(isAbortError(cancelled)).toBe(true)
    expect(getErrorDetail(cancelled)).toBe('Request cancelled.')
    expect(getErrorDetail(null, 'fallback')).toBe('fallback')
    expect(getErrorDetail(new Error('boom'))).toBe('boom')
  })
})

describe('analysisStreamUrl', () => {
  it('builds the SSE URL with an encoded ticker and refresh flag', () => {
    expect(API_URL).toBe('http://localhost:8000')
    expect(analysisStreamUrl('BRK.B')).toBe('http://localhost:8000/analysis/BRK.B/stream?refresh=false')
    expect(analysisStreamUrl('A/B', { refresh: true })).toBe('http://localhost:8000/analysis/A%2FB/stream?refresh=true')
  })
})
