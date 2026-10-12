import { Sparkline } from '../../components/charts'
import { Async, Card, ClientStatusBadge, Empty, Health, Kpi, Link, PageHeader, Progress } from '../../components/ui'
import { api } from '../../lib/api'
import { useUser } from '../../lib/auth'
import { money, relative, signedPct } from '../../lib/format'
import { navigate } from '../../lib/router'
import { useApi } from '../../lib/useApi'

export function Dashboard() {
  const user = useUser()
  const state = useApi(() => api.dashboard(), [])
  const firstName = user.name.split(' ')[0]

  return (
    <>
      <PageHeader
        eyebrow="Agency dashboard"
        title={`Good to see you, ${firstName}`}
        description="Every client at a glance: health, approvals and what moved this week."
      />
      <Async state={state} label="Loading dashboard…">
        {(data) => {
          const live = data.clients.filter((c) => c.status !== 'onboarding')
          const waiting = [...data.clients]
            .filter((c) => c.approvals_waiting + c.internal_review + c.changes_requested > 0)
            .sort((a, b) => b.approvals_waiting - a.approvals_waiting)
          return (
            <div className="stack">
              <div className="grid kpis">
                <Kpi label="Active clients" value={data.totals.active_clients} />
                <Kpi label="Onboarding" value={data.totals.onboarding_clients} />
                <Kpi label="Published (7 days)" value={data.totals.published_this_week} />
                <Kpi label="Awaiting client approval" value={data.totals.awaiting_approval} />
                <Kpi label="Leads this month" value={data.totals.leads_this_month} />
                <Kpi label="Open pipeline" value={money(data.totals.pipeline_value)} />
              </div>

              <Card title="Client health" subtitle="Cadence, growth and stuck approvals, scored 0-100" bodyless>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Client</th>
                        <th>Status</th>
                        <th>Health</th>
                        <th>Waiting on client</th>
                        <th>Impressions (12 wks)</th>
                        <th className="num">4-wk change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {live.map((row) => (
                        <tr key={row.id} className="clickable" onClick={() => navigate(`/clients/${row.id}`)}>
                          <td>
                            <strong>{row.name}</strong>
                            <div className="subtle">
                              {row.company} · {row.industry}
                            </div>
                          </td>
                          <td>
                            <ClientStatusBadge status={row.status} />
                          </td>
                          <td>
                            <Health score={row.health} />
                          </td>
                          <td>{row.approvals_waiting ? <strong>{row.approvals_waiting}</strong> : <span className="subtle">0</span>}</td>
                          <td>
                            <Sparkline values={row.impressions_series} />
                          </td>
                          <td className="num">
                            <span
                              className={`delta ${(row.impressions_change_pct ?? 0) > 0 ? 'up' : (row.impressions_change_pct ?? 0) < 0 ? 'down' : 'flat'}`}
                            >
                              {signedPct(row.impressions_change_pct)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {live.length === 0 ? <Empty compact title="No live clients yet" /> : null}
              </Card>

              <Card
                title="Onboarding pipeline"
                subtitle={`${data.totals.onboarding_clients} clients getting set up`}
                actions={<Link to="/clients?status=onboarding">View all</Link>}
                bodyless
              >
                <div className="board" style={{ padding: 16 }}>
                  {data.onboarding_pipeline.map((column) => (
                    <div className="board-col" key={column.step} style={{ minHeight: 100 }}>
                      <div className="board-col-header">
                        <span>{column.label}</span>
                        <span className="subtle">{column.clients.length}</span>
                      </div>
                      {column.clients.map((client) => (
                        <button
                          type="button"
                          className="board-card"
                          key={client.id}
                          onClick={() => navigate(`/clients/${client.id}/onboarding`)}
                        >
                          <span className="title">{client.name}</span>
                          <span className="subtle">{client.company}</span>
                          <Progress value={client.onboarding_pct} label="Onboarding progress" />
                        </button>
                      ))}
                    </div>
                  ))}
                </div>
              </Card>

              <div className="grid cols-2">
                <Card
                  title="Approvals waiting"
                  subtitle={`${data.totals.internal_review} in internal review · ${data.totals.awaiting_approval} with clients · ${data.totals.changes_requested} changes requested`}
                  actions={<Link to="/approvals">Open queues</Link>}
                  bodyless
                >
                  {waiting.length ? (
                    <ul className="list">
                      {waiting.map((row) => (
                        <li key={row.id} className="clickable" onClick={() => navigate(`/approvals?client=${row.id}`)}>
                          <div className="grow">
                            <strong>{row.name}</strong>
                            <div className="subtle">{row.company}</div>
                          </div>
                          <span className="chip">{row.internal_review} internal</span>
                          <span className="chip">{row.approvals_waiting} with client</span>
                          {row.changes_requested ? <span className="chip">{row.changes_requested} changes</span> : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <Empty compact title="Nothing waiting" />
                  )}
                </Card>

                <Card title="Activity" subtitle="Latest across all clients" bodyless>
                  {data.activity.length ? (
                    <ul className="list">
                      {data.activity.map((item) => (
                        <li key={item.id}>
                          <div className="grow">
                            <div>{item.message}</div>
                            <div className="subtle">
                              {item.client_name ? `${item.client_name} · ` : ''}
                              {relative(item.created_at)}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <Empty compact title="No activity yet" />
                  )}
                </Card>
              </div>
            </div>
          )
        }}
      </Async>
    </>
  )
}
