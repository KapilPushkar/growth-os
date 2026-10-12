import { createContext, useContext } from 'react'
import type { Me } from './types'

export interface AuthState {
  user: Me | null
  ready: boolean
  login: (email: string, password: string) => Promise<Me>
  logout: () => void
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>')
  return value
}

/** The signed-in user; only call below the login gate. */
export function useUser(): Me {
  const { user } = useAuth()
  if (!user) throw new Error('useUser called without a signed-in user')
  return user
}

export const isTeam = (user: Me) => user.role !== 'client'
