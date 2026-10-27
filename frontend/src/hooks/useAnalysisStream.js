import { useCallback, useEffect, useReducer } from 'react'
import { API_URL, analysisStreamUrl } from '../services/api'
import { analysisStreamReducer, createInitialState } from '../state/analysisStream'

// Named events we act on; anything else the server sends is ignored.
const EVENTS = ['stage', 'source', 'llm', 'report']

/**
 * Subscribes to the analysis SSE stream for `ticker`.
 * Returns `[state, restart]`; `restart({ refresh: true })` forces a new report.
 * The EventSource is closed on unmount, on ticker change and on restart.
 */
export function useAnalysisStream(ticker) {
  const [state, dispatch] = useReducer(analysisStreamReducer, undefined, createInitialState)
  const { runId, refresh } = state

  useEffect(() => {
    const source = new EventSource(analysisStreamUrl(ticker, { refresh }))
    let closed = false
    const close = () => {
      closed = true
      source.close()
    }

    const parse = (event) => {
      try {
        return JSON.parse(event.data)
      } catch {
        return null
      }
    }

    const listeners = EVENTS.map((type) => {
      const listener = (event) => {
        const payload = parse(event)
        if (!payload || closed) return
        if (type === 'report') close()
        dispatch({ type, payload })
      }
      source.addEventListener(type, listener)
      return [type, listener]
    })

    // `error` is both the backend's named event (has data) and the browser's
    // connection error (no data). Either way the stream is over: EventSource
    // would otherwise reconnect and start a whole new analysis.
    const onError = (event) => {
      if (closed) return
      const payload = typeof event.data === 'string' ? parse(event) : null
      close()
      if (payload) {
        dispatch({ type: 'error', payload })
      } else {
        dispatch({
          type: 'connection_lost',
          detail: `Lost connection to the analysis stream (${API_URL}). The backend may be offline or restarting.`,
        })
      }
    }
    source.addEventListener('error', onError)

    return () => {
      listeners.forEach(([type, listener]) => source.removeEventListener(type, listener))
      source.removeEventListener('error', onError)
      close()
    }
  }, [ticker, runId, refresh])

  const restart = useCallback((options = {}) => {
    dispatch({ type: 'restart', refresh: Boolean(options.refresh) })
  }, [])

  return [state, restart]
}
