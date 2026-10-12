import { useEffect } from 'react'
import { AuthProvider } from './components/AuthProvider'
import { Layout } from './components/Layout'
import { MonthCalendar } from './components/MonthCalendar'
import { ReportView } from './components/ReportView'
import { ToastProvider } from './components/ToastProvider'
import { Empty, Link, Loading, PageHeader } from './components/ui'
import { isTeam, useAuth } from './lib/auth'
import { matchPath, navigate, useLocation } from './lib/router'
import type { Me } from './lib/types'
import { ClientApprovals } from './pages/client/ClientApprovals'
import { ClientLeads } from './pages/client/ClientLeads'
import { ClientHome } from './pages/client/Home'
import { Preferences } from './pages/client/Preferences'
import { Login } from './pages/Login'
import { Approvals } from './pages/team/Approvals'
import { Calendar } from './pages/team/Calendar'
import { ClientWorkspace } from './pages/team/ClientWorkspace'
import { Clients } from './pages/team/Clients'
import { Dashboard } from './pages/team/Dashboard'
import { Leads } from './pages/team/Leads'

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Root />
      </AuthProvider>
    </ToastProvider>
  )
}

function Root() {
  const { user, ready } = useAuth()
  const { path } = useLocation()

  useEffect(() => {
    if (ready && user && path === '/login') navigate('/')
  }, [ready, user, path])

  if (!ready) return <Loading label="Starting Growth OS…" />
  if (!user) return <Login />
  return (
    <Layout>
      <Page user={user} path={path} />
    </Layout>
  )
}

function Page({ user, path }: { user: Me; path: string }) {
  if (isTeam(user)) {
    if (path === '/' || path === '/login') return <Dashboard />
    if (path === '/clients') return <Clients />
    const workspace = matchPath('/clients/:id/:tab?', path)
    if (workspace && /^\d+$/.test(workspace.id)) {
      return <ClientWorkspace key={workspace.id} clientId={Number(workspace.id)} tab={workspace.tab ?? ''} />
    }
    if (path === '/approvals') return <Approvals />
    if (path === '/calendar') return <Calendar />
    if (path === '/leads') return <Leads />
    return <NotFound />
  }

  const clientId = user.client_id!
  if (path === '/' || path === '/login') return <ClientHome />
  if (path === '/approvals') return <ClientApprovals />
  if (path === '/calendar') {
    return (
      <>
        <PageHeader eyebrow="Calendar" title="What's going out" description="Your scheduled and published posts." />
        <MonthCalendar clientId={clientId} />
      </>
    )
  }
  if (path === '/leads') return <ClientLeads />
  if (path === '/report') return <ReportView clientId={clientId} />
  if (path === '/preferences') return <Preferences />
  return <NotFound />
}

function NotFound() {
  return (
    <div className="card">
      <Empty title="Page not found" action={<Link to="/">Go home</Link>}>
        That link does not match anything in Growth OS.
      </Empty>
    </div>
  )
}
