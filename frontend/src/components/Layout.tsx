import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../lib/api'
import { isTeam, useAuth, useUser } from '../lib/auth'
import { humanize } from '../lib/format'
import { useLocation } from '../lib/router'
import type { AiStatus } from '../lib/types'
import { Link } from './ui'

interface NavItem {
  to: string
  label: string
  exact?: boolean
  count?: number
}

export function Layout({ children }: { children: ReactNode }) {
  const user = useUser()
  const { logout } = useAuth()
  const { path } = useLocation()
  const team = isTeam(user)
  // The menu belongs to the page it was opened on, so navigating closes it.
  const [openOn, setOpenOn] = useState<string | null>(null)
  const open = openOn === path
  const [waiting, setWaiting] = useState(0)
  const [ai, setAi] = useState<AiStatus | null>(null)

  // Refresh the approvals badge whenever the page changes.
  useEffect(() => {
    api
      .approvals()
      .then((queues) => setWaiting(team ? queues.internal_review.length : queues.client_review.length))
      .catch(() => undefined)
  }, [path, team])

  useEffect(() => {
    if (team) api.ai.status().then(setAi).catch(() => undefined)
  }, [team])

  const nav: NavItem[] = team
    ? [
        { to: '/', label: 'Dashboard', exact: true },
        { to: '/clients', label: 'Clients' },
        { to: '/approvals', label: 'Approvals', count: waiting },
        { to: '/calendar', label: 'Calendar' },
        { to: '/leads', label: 'Leads' },
      ]
    : [
        { to: '/', label: 'Home', exact: true },
        { to: '/approvals', label: 'Approvals', count: waiting },
        { to: '/calendar', label: 'Calendar' },
        { to: '/leads', label: 'Leads' },
        { to: '/report', label: 'Report' },
        { to: '/preferences', label: 'Preferences' },
      ]

  return (
    <div className={`app-shell${open ? ' nav-open' : ''}`}>
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">G</span>
          Growth OS
        </div>
        <nav className="nav" aria-label="Main">
          <div className="nav-label">{team ? 'Agency console' : user.client?.company ?? 'Your account'}</div>
          {nav.map((item) => (
            <Link key={item.to} to={item.to} exact={item.exact}>
              <span>{item.label}</span>
              {item.count ? <span className="count">{item.count}</span> : null}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <strong>{user.name}</strong>
          <span>{team ? humanize(user.role) : user.client?.title || 'Client'}</span>
          {team && ai ? (
            <span title={ai.model ?? 'Built-in templates'}>
              AI: {ai.mode === 'llm' ? `${humanize(ai.provider)} (${ai.model})` : 'template mode'}
            </span>
          ) : null}
          <button type="button" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      {open ? <div className="overlay" onClick={() => setOpenOn(null)} /> : null}
      <div className="grow">
        <header className="topbar">
          <button type="button" className="btn btn-sm" onClick={() => setOpenOn(path)} aria-label="Open menu">
            ☰
          </button>
          <strong>Growth OS</strong>
        </header>
        <main className="main">{children}</main>
      </div>
    </div>
  )
}
