import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from './toast'

export interface ApiState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
  setData: (updater: T | ((current: T | null) => T)) => void
}

interface Result<T> {
  requestId: string
  data: T | null
  error: string | null
}

/**
 * Load data on mount and whenever `deps` change. Previous data stays visible
 * while a new request is in flight, and responses from superseded requests
 * are ignored so fast filter changes never show the wrong data.
 */
export function useApi<T>(load: () => Promise<T>, deps: unknown[]): ApiState<T> {
  const [version, setVersion] = useState(0)
  const [result, setResult] = useState<Result<T>>({ requestId: '', data: null, error: null })
  const loadRef = useRef(load)

  // Always call the latest loader without making it a dependency.
  useEffect(() => {
    loadRef.current = load
  })

  const depsKey = JSON.stringify(deps)
  const requestId = `${depsKey}#${version}`

  useEffect(() => {
    let active = true
    loadRef
      .current()
      .then((data) => {
        if (active) setResult({ requestId, data, error: null })
      })
      .catch((err: unknown) => {
        if (active) setResult((current) => ({ requestId, data: current.data, error: errorMessage(err) }))
      })
    return () => {
      active = false
    }
  }, [requestId])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  const setData = useCallback((updater: T | ((current: T | null) => T)) => {
    setResult((current) => ({
      ...current,
      data: typeof updater === 'function' ? (updater as (c: T | null) => T)(current.data) : updater,
    }))
  }, [])

  const settled = result.requestId === requestId
  return {
    data: result.data,
    error: settled ? result.error : null,
    loading: !settled,
    reload,
    setData,
  }
}
