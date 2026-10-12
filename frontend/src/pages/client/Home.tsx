import { Async, Button, Card, Empty, Kpi, Link, StageBadge } from '../../components/ui'
import { api } from '../../lib/api'
import { useUser } from '../../lib/auth'
import { CHANNEL_LABELS, dateTime, money, pct, relative } from '../../lib/format'
import { navigate } from '../../lib/router'
import { useApi } from '../../lib/useApi'

const RESULT_KPIS = ['impressions', 'engagements', 'leads', 'meetings', 'ai_visibility']

export function ClientHome() {
  const user = useUser()
  const clientId = user.client_id!
  const approvals = useApi(() => api.approvals(), [])
  const impact = useApi(() => api.clients.impact(clientId), [clientId])
  const upcoming = useApi(() => api.content.list({ status: 'scheduled' }), [])
  const leads = useApi(() => api.leads.list(), [])
  const waiting = approvals.data?.client_review.length ?? 0
  const firstName = user.name.replace(/^Dr\.?\s+/i, '').split(' ')[0]

  return (
    <div className="stack">
      <section className="hero">
        <div className="stack tight">
          <span style={{ color: '#8fd3b8', fontWeight: 600 }}>Welcome back, {firstName}</span>
          <h2>
            {approvals.loading && !approvals.data
              ? 'Checking your approvals…'
              : waiting
                ? `${waiting} post${waiting === 1 ? '' : 's'} need${waiting === 1 ? 's' : ''} your approval`
                : "You're all caught up"}
          </h2>
          <p>
            {waiting
              ? 'Review them in a couple of minutes: approve, or tell us what to change.'
              : 'Nothing is waiting on you. We will let you know when new drafts are ready.'}
          </p>
        </div>
        {waiting ? (
          <Button variant="primary" size="lg" onClick={() => navigate('/approvals')}>
            Review now
          </Button>
        ) : null}
      </section>

      <div>
        <div className="row between" style={{ marginBottom: 12 }}>
          <h2>Your results, last 4 weeks</h2>
          <Link to="/report">Full report</Link>
        </div>
        <Async state={impact} label="Loading results…">
          {(data) =>
            data.series.length ? (
              <div className="grid kpis">
                {data.kpis
                  .filter((kpi) => RESULT_KPIS.includes(kpi.key))
                  .map((kpi) => (
                    <Kpi
                      key={kpi.key}
                      label={kpi.label}
                      value={kpi.key === 'ai_visibility' ? pct(kpi.current, 1) : kpi.current}
                      change={kpi.change_pct}
                    />
                  ))}
              </div>
            ) : (
              <div className="card">
                <Empty title="Results start once you're live">Your first weekly numbers will appear here.</Empty>
              </div>
            )
          }
        </Async>
      </div>

      <div className="grid cols-2">
        <Card title="Coming up" subtitle="Approved and scheduled to publish" actions={<Link to="/calendar">Calendar</Link>} bodyless>
          <Async state={upcoming}>
            {(items) => {
              const next = [...items]
                .sort((a, b) => (a.scheduled_at ?? '').localeCompare(b.scheduled_at ?? ''))
                .slice(0, 5)
              return next.length ? (
                <ul className="list">
                  {next.map((piece) => (
                    <li key={piece.id}>
                      <div className="grow">
                        <strong>{piece.title}</strong>
                        <div className="subtle">{CHANNEL_LABELS[piece.channel]}</div>
                      </div>
                      <span className="muted">{dateTime(piece.scheduled_at)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty compact title="Nothing scheduled yet" />
              )
            }}
          </Async>
        </Card>
        <Card title="Recent leads" subtitle="People your content brought in" actions={<Link to="/leads">All leads</Link>} bodyless>
          <Async state={leads}>
            {(items) =>
              items.length ? (
                <ul className="list">
                  {items.slice(0, 5).map((lead) => (
                    <li key={lead.id}>
                      <div className="grow">
                        <strong>{lead.name}</strong>
                        <div className="subtle">
                          {lead.title} · {lead.company} · {relative(lead.created_at)}
                        </div>
                      </div>
                      {lead.deal_value ? <span className="mono muted">{money(lead.deal_value)}</span> : null}
                      <StageBadge stage={lead.stage} />
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty compact title="No leads yet" />
              )
            }
          </Async>
        </Card>
      </div>
    </div>
  )
}
