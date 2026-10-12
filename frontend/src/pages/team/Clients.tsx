import { useMemo, useState } from 'react'
import { ClientWizard } from '../../components/ClientWizard'
import { Button, Card, ClientStatusBadge, Empty, ErrorState, Health, Loading, PageHeader, Progress } from '../../components/ui'
import { api } from '../../lib/api'
import { CHANNEL_LABELS } from '../../lib/format'
import { navigate, useLocation } from '../../lib/router'
import { useApi } from '../../lib/useApi'

export function Clients() {
  const { query } = useLocation()
  const [status, setStatus] = useState(query.get('status') ?? '')
  const [search, setSearch] = useState('')
  const [industry, setIndustry] = useState('')
  const [wizard, setWizard] = useState(false)
  const state = useApi(() => api.clients.list({ status: status || undefined }), [status])

  const industries = useMemo(() => [...new Set((state.data ?? []).map((c) => c.industry).filter(Boolean))].sort(), [state.data])
  const rows = (state.data ?? []).filter((client) => {
    const text = `${client.name} ${client.company}`.toLowerCase()
    return (!search || text.includes(search.toLowerCase())) && (!industry || client.industry === industry)
  })

  return (
    <>
      <PageHeader
        eyebrow="Clients"
        title="Client roster"
        description="Founders and executives we run growth for, from first intake to live."
        actions={
          <Button variant="primary" onClick={() => setWizard(true)}>
            New client
          </Button>
        }
      />
      <Card
        bodyless
        actions={
          <>
            <input
              className="input"
              style={{ width: 220 }}
              placeholder="Search name or company"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search clients"
            />
            <select className="select" style={{ width: 160 }} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="onboarding">Onboarding</option>
              <option value="paused">Paused</option>
            </select>
            <select className="select" style={{ width: 170 }} value={industry} onChange={(e) => setIndustry(e.target.value)} aria-label="Industry">
              <option value="">All industries</option>
              {industries.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </>
        }
        title={`${rows.length} client${rows.length === 1 ? '' : 's'}`}
      >
        {state.error ? (
          <ErrorState message={state.error} onRetry={state.reload} />
        ) : !state.data ? (
          <Loading />
        ) : rows.length === 0 ? (
          <Empty title="No clients match" action={<Button onClick={() => setWizard(true)}>Add a client</Button>}>
            Try a different filter, or add a new client.
          </Empty>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Industry</th>
                  <th>Status</th>
                  <th>Health</th>
                  <th style={{ width: 160 }}>Onboarding</th>
                  <th>Channels</th>
                  <th>Account manager</th>
                  <th className="num">Waiting</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((client) => (
                  <tr key={client.id} className="clickable" onClick={() => navigate(`/clients/${client.id}`)}>
                    <td>
                      <strong>{client.name}</strong>
                      <div className="subtle">
                        {client.title ? `${client.title}, ` : ''}
                        {client.company}
                      </div>
                    </td>
                    <td>{client.industry}</td>
                    <td>
                      <ClientStatusBadge status={client.status} />
                    </td>
                    <td>
                      <Health score={client.health} />
                    </td>
                    <td>
                      <div className="stack tight">
                        <Progress value={client.onboarding_pct} label="Onboarding" />
                        <span className="subtle">{client.onboarding_pct}%</span>
                      </div>
                    </td>
                    <td className="subtle">{client.channels.map((c) => CHANNEL_LABELS[c]).join(', ')}</td>
                    <td>{client.account_manager?.name ?? <span className="subtle">Unassigned</span>}</td>
                    <td className="num">{client.approvals_waiting || <span className="subtle">0</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {wizard ? <ClientWizard onClose={() => setWizard(false)} onCreated={state.reload} /> : null}
    </>
  )
}
