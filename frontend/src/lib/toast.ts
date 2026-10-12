import { createContext, useContext } from 'react'

export type ToastKind = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  kind: ToastKind
  message: string
}

export interface ToastApi {
  success: (message: string) => void
  error: (error: unknown) => void
  info: (message: string) => void
}

export const ToastContext = createContext<ToastApi | null>(null)

export function useToast(): ToastApi {
  const value = useContext(ToastContext)
  if (!value) throw new Error('useToast must be used inside <ToastProvider>')
  return value
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return typeof error === 'string' ? error : 'Something went wrong'
}
