import { useCallback, useEffect, useEffectEvent, useState } from 'react'
import { isAbortError } from '../services/api'

/**
 * Runs `fetcher(signal)` whenever `key` changes and aborts the previous request.
 *
 * Results are tagged with the key that produced them, so `loading` is derived
 * (the latest result belongs to an older key) instead of being set in the effect,
 * and a stale error can never leak into the next request. Pass `key = null` to
 * stay idle until something (for example a button) provides a key.
 */
export function useRequest(key, fetcher) {
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState({ key: null, data: undefined, error: null })

  const requestKey = key == null ? null : `${key}#${attempt}`
  const run = useEffectEvent((signal) => fetcher(signal))

  useEffect(() => {
    if (requestKey == null) return undefined
    const controller = new AbortController()
    run(controller.signal).then(
      (data) => setResult({ key: requestKey, data, error: null }),
      (error) => {
        if (!controller.signal.aborted && !isAbortError(error)) {
          setResult({ key: requestKey, data: undefined, error })
        }
      },
    )
    return () => controller.abort()
  }, [requestKey])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  const settled = requestKey != null && result.key === requestKey

  return {
    data: settled ? result.data : undefined,
    error: settled ? result.error : null,
    loading: requestKey != null && !settled,
    reload,
  }
}
