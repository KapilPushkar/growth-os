import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, onUnauthorized, tokenStore } from '../lib/api'
import { AuthContext, type AuthState } from '../lib/auth'
import type { Me } from '../lib/types'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  // With no stored token there is nothing to restore, so the app is ready at once.
  const [ready, setReady] = useState(() => tokenStore.get() === null)

  const logout = useCallback(() => {
    tokenStore.set(null)
    setUser(null)
    window.location.hash = '/login'
  }, [])

  useEffect(() => {
    onUnauthorized(logout)
    if (!tokenStore.get()) return
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.set(null))
      .finally(() => setReady(true))
  }, [logout])

  const login = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password)
    tokenStore.set(result.access_token)
    setUser(result.user)
    return result.user
  }, [])

  const value = useMemo<AuthState>(() => ({ user, ready, login, logout }), [user, ready, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
