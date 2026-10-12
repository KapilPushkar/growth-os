import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { ToastContext, errorMessage, type Toast, type ToastApi, type ToastKind } from '../lib/toast'

const DISMISS_AFTER_MS = 4500

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const push = useCallback((kind: ToastKind, message: string) => {
    const id = nextId.current++
    setToasts((current) => [...current.slice(-3), { id, kind, message }])
    window.setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), DISMISS_AFTER_MS)
  }, [])

  const value = useMemo<ToastApi>(
    () => ({
      success: (message) => push('success', message),
      info: (message) => push('info', message),
      error: (error) => push('error', errorMessage(error)),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.kind}`} role={toast.kind === 'error' ? 'alert' : 'status'}>
            <span className="dot" aria-hidden />
            <span>{toast.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
