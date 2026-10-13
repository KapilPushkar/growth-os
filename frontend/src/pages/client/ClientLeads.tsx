import { useState } from 'react'
import { LeadDrawer } from '../../components/Leads'
import { Async, Badge, Card, Empty, PageHeader, StageBadge } from '../../components/ui'
import { api } from '../../lib/api'
import { SOURCE_LABELS, money, plural, relative } from '../../lib/format'
import type { Lead } from '../../lib/types'
import { useApi } from '../../lib/useApi'

export function ClientLeads() {
  const state = useApi(() => api.leads.pipeline(), [])
  const [selected, setSelected] = useState<Lead | null>(null)

  return (
    <>
      <PageHeader
        eyebrow="Leads"
        title="Your pipeline"
        description="People who came in through your content and outreach. Add notes for the team anytime."
      />
      <Async state={state} label="Loading leads…">
        {(pipeline) => {
          const leads = pipeline.stages.flatMap((stage) => stage.leads)
          return (
            <Card
              bodyless
              title={plural(pipeline.summary.total, 'lead')}
              actions={
                <>
                  <Badge tone="blue" plain>
                    Open {money(pipeline.summary.open_value)}
                  </Badge>
                  <Badge tone="green" plain>
                    Won {money(pipeline.summary.won_value)}
                  </Badge>
                </>
              }
            >
              {leads.length === 0 ? (
                <Empty title="No leads yet">Leads from your posts will show up here.</Empty>
              ) : (
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Lead</th>
                        <th>Stage</th>
                        <th>Source</th>
                        <th className="num">Value</th>
                        <th>Updated</th>
                        <th>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leads.map((lead) => (
                        <tr key={lead.id} className="clickable" onClick={() => setSelected(lead)}>
                          <td>
                            <strong>{lead.name}</strong>
                            <div className="subtle">
                              {lead.title} · {lead.company}
                            </div>
                          </td>
                          <td>
                            <StageBadge stage={lead.stage} />
                          </td>
                          <td>{SOURCE_LABELS[lead.source]}</td>
                          <td className="num">{money(lead.deal_value)}</td>
                          <td className="subtle">{relative(lead.stage_changed_at)}</td>
                          <td className="subtle" style={{ maxWidth: 240 }}>
                            {lead.notes || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          )
        }}
      </Async>
      {selected ? (
        <LeadDrawer
          key={selected.id}
          lead={selected}
          onClose={() => setSelected(null)}
          onChanged={(lead) => {
            setSelected(lead)
            state.reload()
          }}
        />
      ) : null}
    </>
  )
}
