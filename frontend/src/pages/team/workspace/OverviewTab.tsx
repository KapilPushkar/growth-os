import { BarList, Funnel, LineChart } from '../../../components/charts'
import { KeywordMovers } from '../../../components/KeywordMovers'
import { Async, Card, Empty, Kpi, SimulatedBadge, StageBadge } from '../../../components/ui'
import { api } from '../../../lib/api'
import { CHANNEL_LABELS, ENGINE_LABELS, date, money, num, pct } from '../../../lib/format'
import type { Client } from '../../../lib/types'
import { useApi } from '../../../lib/useApi'

const weekLabel = (value: string) => new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })

export function OverviewTab({ client }: { client: Client }) {
  const state = useApi(() => api.clients.impact(client.id), [client.id])

  return (
    <Async state={state} label="Loading impact…">
      {(impact) => {
        if (!impact.series.length) {
          return (
            <div className="card">
              <Empty title="No results yet">
                Impact charts appear once {client.name} is live and the first weekly snapshot lands. Finish onboarding to
                get started.
              </Empty>
            </div>
          )
        }
        const labels = impact.series.map((s) => weekLabel(s.week_start))
        return (
          <div className="stack">
            <p className="subtle">Last {impact.weeks} weeks compared with the {impact.weeks} before.</p>
            <div className="grid kpis">
              {impact.kpis.map((kpi) => (
                <Kpi
                  key={kpi.key}
                  label={kpi.label}
                  value={kpi.key === 'ai_visibility' ? pct(kpi.current, 1) : kpi.current}
                  change={kpi.change_pct}
                />
              ))}
            </div>
            <div className="grid cols-2">
              <Card title="Reach" subtitle="Weekly impressions and engagements">
                <LineChart
                  labels={labels}
                  series={[
                    { name: 'Impressions', values: impact.series.map((s) => s.impressions) },
                    { name: 'Engagements', values: impact.series.map((s) => s.engagements) },
                  ]}
                />
              </Card>
              <Card title="Audience" subtitle="Total followers by week">
                <LineChart labels={labels} series={[{ name: 'Followers', values: impact.series.map((s) => s.followers) }]} />
              </Card>
              <Card title="Pipeline" subtitle="Weekly leads and meetings">
                <LineChart
                  labels={labels}
                  series={[
                    { name: 'Leads', values: impact.series.map((s) => s.leads), color: '#0f6b55' },
                    { name: 'Meetings', values: impact.series.map((s) => s.meetings), color: '#c08a2b' },
                  ]}
                />
              </Card>
              <Card title="Funnel" subtitle={`Last ${impact.weeks} weeks: content to revenue`}>
                <Funnel steps={impact.funnel} />
              </Card>
            </div>
            <div className="grid cols-3">
              <Card title="Top posts" bodyless>
                {impact.top_posts.length ? (
                  <ul className="list">
                    {impact.top_posts.map((post) => (
                      <li key={post.id}>
                        <div className="grow">
                          <strong>{post.title}</strong>
                          <div className="subtle">
                            {CHANNEL_LABELS[post.channel]} · {date(post.published_at)}
                          </div>
                        </div>
                        <span className="mono">{num(post.metrics.engagements)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Empty compact title="Nothing published yet" />
                )}
              </Card>
              <Card title="Keyword movers" actions={<SimulatedBadge />} bodyless>
                <KeywordMovers keywords={impact.keyword_movers} />
              </Card>
              <Card title="AI visibility by engine" subtitle="Latest check per buyer question">
                {impact.geo.length ? (
                  <BarList
                    items={impact.geo.map((g) => ({ label: ENGINE_LABELS[g.engine], value: g.visibility_pct, note: g.method }))}
                    max={100}
                    format={(v) => pct(v)}
                  />
                ) : (
                  <Empty compact title="No GEO checks yet" />
                )}
              </Card>
            </div>
            <Card title="Lead pipeline" subtitle={`${impact.leads.total} leads · ${money(impact.leads.open_value)} open · ${money(impact.leads.won_value)} won`}>
              <div className="row wrap" style={{ gap: 12 }}>
                {impact.leads.by_stage.map((stage) => (
                  <div key={stage.stage} className="row">
                    <StageBadge stage={stage.stage} />
                    <strong>{stage.count}</strong>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )
      }}
    </Async>
  )
}
