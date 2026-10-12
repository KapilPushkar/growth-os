import { useState } from 'react'
import { api } from '../lib/api'
import { CHANNEL_LABELS, ENGINE_LABELS, date, money, num, pct } from '../lib/format'
import { useApi } from '../lib/useApi'
import { BarList, LineChart } from './charts'
import { KeywordMovers } from './KeywordMovers'
import { Async, Button, Card, Empty, Kpi, PageHeader, SimulatedBadge, SourceBadge } from './ui'

const PERIODS = [30, 60, 90]

function weekLabel(value: string) {
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export function ReportView({ clientId }: { clientId: number }) {
  const [days, setDays] = useState(30)
  const state = useApi(() => api.clients.report(clientId, days), [clientId, days])

  return (
    <Async state={state} label="Preparing report…">
      {(report) => (
        <div className="stack">
          <PageHeader
            eyebrow={`${report.client.company} · ${report.client.industry}`}
            title={`Growth report for ${report.client.name}`}
            description={`${date(report.period.start)} – ${date(report.period.end)} (${report.period.days} days)`}
            actions={
              <>
                <div className="segmented">
                  {PERIODS.map((period) => (
                    <button
                      key={period}
                      type="button"
                      className={period === days ? 'active' : ''}
                      onClick={() => setDays(period)}
                    >
                      {period} days
                    </button>
                  ))}
                </div>
                <Button variant="primary" onClick={() => window.print()}>
                  Save as PDF
                </Button>
              </>
            }
          />

          <div className="grid kpis">
            {report.kpis
              .filter((kpi) => ['impressions', 'engagements', 'followers', 'leads', 'meetings', 'ai_visibility'].includes(kpi.key))
              .map((kpi) => (
                <Kpi
                  key={kpi.key}
                  label={kpi.label}
                  value={kpi.key === 'ai_visibility' ? pct(kpi.current, 1) : kpi.current}
                  change={kpi.change_pct}
                />
              ))}
          </div>

          <div className="grid main-side">
            <Card title="Executive summary" actions={<SourceBadge source={report.summary_source} />}>
              <div className="stack">
                <p className="prose" style={{ fontSize: 15 }}>
                  {report.summary}
                </p>
                <div>
                  <div className="section-title">Next steps</div>
                  <ol className="stack tight" style={{ margin: 0, paddingLeft: 20 }}>
                    {report.next_steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </div>
              </div>
            </Card>
            <Card title="Highlights">
              <div className="stack tight">
                <Highlight label="Posts published" value={num(report.highlights.posts_published)} />
                <Highlight label="New leads" value={num(report.highlights.new_leads)} />
                <Highlight label="Meetings booked" value={num(report.highlights.meetings_booked)} />
                <Highlight label="Deals won" value={num(report.highlights.deals_won)} />
                <Highlight label="Won value" value={money(report.highlights.won_value)} />
              </div>
            </Card>
          </div>

          <Card title="Weekly reach" subtitle="Impressions and engagements per week">
            <LineChart
              labels={report.series.map((s) => weekLabel(s.week_start))}
              series={[
                { name: 'Impressions', values: report.series.map((s) => s.impressions) },
                { name: 'Engagements', values: report.series.map((s) => s.engagements) },
              ]}
            />
          </Card>

          <div className="grid cols-2">
            <Card title="Top content" bodyless>
              {report.top_content.length ? (
                <ul className="list">
                  {report.top_content.map((post) => (
                    <li key={post.id}>
                      <div className="grow">
                        <strong>{post.title}</strong>
                        <div className="subtle">
                          {CHANNEL_LABELS[post.channel]} · {date(post.published_at)}
                        </div>
                      </div>
                      <div className="mono" style={{ textAlign: 'right' }}>
                        <div>{num(post.metrics.engagements)} eng.</div>
                        <div className="subtle">{num(post.metrics.impressions)} impr.</div>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty compact title="Nothing published in this period" />
              )}
            </Card>
            <Card title="Leads won" bodyless>
              {report.leads_won.length ? (
                <ul className="list">
                  {report.leads_won.map((lead) => (
                    <li key={lead.id}>
                      <div className="grow">
                        <strong>{lead.name}</strong>
                        <div className="subtle">
                          {lead.title} · {lead.company}
                        </div>
                      </div>
                      <strong className="mono">{money(lead.deal_value)}</strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty compact title="No deals closed in this period" />
              )}
            </Card>
          </div>

          <div className="grid cols-2">
            <Card title="Keyword movers" actions={<SimulatedBadge />} bodyless>
              <KeywordMovers keywords={report.keyword_movers} />
            </Card>
            <Card title="AI-assistant visibility" subtitle="Share of tracked buyer questions that name you">
              {report.geo.length ? (
                <BarList
                  items={report.geo.map((g) => ({ label: ENGINE_LABELS[g.engine], value: g.visibility_pct }))}
                  max={100}
                  format={(v) => pct(v)}
                />
              ) : (
                <Empty compact title="No GEO checks yet" />
              )}
            </Card>
          </div>
        </div>
      )}
    </Async>
  )
}

function Highlight({ label, value }: { label: string; value: string }) {
  return (
    <div className="row between">
      <span className="muted">{label}</span>
      <strong className="mono">{value}</strong>
    </div>
  )
}
