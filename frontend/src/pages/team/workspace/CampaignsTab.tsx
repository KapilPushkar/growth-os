import { useState } from 'react'
import { Async, Badge, Button, Card, Empty, Field, Modal, Progress } from '../../../components/ui'
import { api } from '../../../lib/api'
import { CAMPAIGN_TYPE_LABELS, CHANNEL_LABELS, KPI_LABELS, date, num } from '../../../lib/format'
import { useToast } from '../../../lib/toast'
import type { Campaign, CampaignStatus, CampaignType, Client } from '../../../lib/types'
import { useApi } from '../../../lib/useApi'

const STATUS_TONE = { planned: 'neutral', active: 'green', paused: 'amber', completed: 'blue' } as const
const KPI_KEYS = ['posts', 'impressions', 'engagements', 'leads', 'meetings']

export function CampaignsTab({ client }: { client: Client }) {
  const toast = useToast()
  const state = useApi(() => api.campaigns.list(client.id), [client.id])
  const [creating, setCreating] = useState(false)

  async function setStatus(campaign: Campaign, status: CampaignStatus) {
    try {
      const updated = await api.campaigns.update(campaign.id, { status })
      state.setData((current) => (current ?? []).map((c) => (c.id === updated.id ? updated : c)))
      toast.success(`Campaign marked ${status}`)
    } catch (error) {
      toast.error(error)
    }
  }

  async function remove(campaign: Campaign) {
    if (!window.confirm(`Delete “${campaign.name}”? Content and leads stay, unlinked.`)) return
    try {
      await api.campaigns.remove(campaign.id)
      state.reload()
      toast.success('Campaign deleted')
    } catch (error) {
      toast.error(error)
    }
  }

  return (
    <div className="stack">
      <div className="row between">
        <p className="muted">Group content and outreach around one goal, with KPI targets tracked from real results.</p>
        <Button variant="primary" onClick={() => setCreating(true)}>
          New campaign
        </Button>
      </div>
      <Async state={state} label="Loading campaigns…">
        {(campaigns) =>
          campaigns.length === 0 ? (
            <div className="card">
              <Empty title="No campaigns yet" action={<Button onClick={() => setCreating(true)}>Create the first one</Button>} />
            </div>
          ) : (
            <div className="grid cols-2">
              {campaigns.map((campaign) => (
                <Card
                  key={campaign.id}
                  title={campaign.name}
                  subtitle={`${date(campaign.start_date)} – ${date(campaign.end_date)}`}
                  actions={
                    <>
                      <Badge tone="violet" plain>
                        {CAMPAIGN_TYPE_LABELS[campaign.type]}
                      </Badge>
                      <Badge tone={STATUS_TONE[campaign.status]}>{campaign.status}</Badge>
                    </>
                  }
                >
                  <div className="stack">
                    {campaign.objective ? <p className="muted">{campaign.objective}</p> : null}
                    {Object.keys(campaign.progress).length ? (
                      <div className="stack tight">
                        {Object.entries(campaign.progress).map(([key, kpi]) => (
                          <div key={key} className="stack tight" style={{ gap: 4 }}>
                            <div className="row between">
                              <span>{KPI_LABELS[key] ?? key}</span>
                              <span className="mono">
                                <strong>{num(kpi.actual)}</strong> <span className="subtle">/ {num(kpi.target)}</span>
                                <span className="subtle"> · {Math.round(kpi.pct)}%</span>
                              </span>
                            </div>
                            <Progress value={kpi.pct} label={KPI_LABELS[key]} />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="subtle">No KPI targets set.</span>
                    )}
                    <div className="row wrap between">
                      <div className="row wrap">
                        {campaign.channels.map((c) => (
                          <span className="chip" key={c}>
                            {CHANNEL_LABELS[c]}
                          </span>
                        ))}
                      </div>
                      <div className="row">
                        <select
                          className="select"
                          style={{ width: 130, minHeight: 28, padding: '2px 8px' }}
                          value={campaign.status}
                          onChange={(e) => void setStatus(campaign, e.target.value as CampaignStatus)}
                          aria-label="Campaign status"
                        >
                          {Object.keys(STATUS_TONE).map((s) => (
                            <option key={s}>{s}</option>
                          ))}
                        </select>
                        <Button size="sm" variant="ghost" onClick={() => void remove(campaign)}>
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )
        }
      </Async>
      {creating ? (
        <NewCampaignModal
          client={client}
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false)
            state.reload()
          }}
        />
      ) : null}
    </div>
  )
}

function NewCampaignModal({ client, onClose, onCreated }: { client: Client; onClose: () => void; onCreated: () => void }) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(() => ({
    name: '',
    type: 'content' as CampaignType,
    status: 'planned' as CampaignStatus,
    objective: '',
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date(Date.now() + 42 * 86400000).toISOString().slice(0, 10),
    kpis: { posts: 12, impressions: 50000, engagements: 0, leads: 0, meetings: 0 } as Record<string, number>,
  }))

  async function submit() {
    setSaving(true)
    try {
      await api.campaigns.create({
        client_id: client.id,
        name: form.name,
        type: form.type,
        status: form.status,
        objective: form.objective,
        channels: client.channels.slice(0, 2),
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        kpi_targets: Object.fromEntries(Object.entries(form.kpis).filter(([, value]) => value > 0)),
      })
      toast.success('Campaign created')
      onCreated()
    } catch (error) {
      toast.error(error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title="New campaign"
      onClose={onClose}
      footer={
        <Button variant="primary" busy={saving} disabled={!form.name.trim()} onClick={submit}>
          Create campaign
        </Button>
      }
    >
      <div className="form-grid">
        <Field label="Name" full>
          <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoFocus />
        </Field>
        <Field label="Type">
          <select className="select" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as CampaignType })}>
            {(Object.keys(CAMPAIGN_TYPE_LABELS) as CampaignType[]).map((type) => (
              <option key={type} value={type}>
                {CAMPAIGN_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Status">
          <select className="select" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as CampaignStatus })}>
            {Object.keys(STATUS_TONE).map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </Field>
        <Field label="Start">
          <input className="input" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
        </Field>
        <Field label="End">
          <input className="input" type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
        </Field>
        <Field label="Objective" full>
          <textarea className="textarea" style={{ minHeight: 64 }} value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} />
        </Field>
        {KPI_KEYS.map((key) => (
          <Field key={key} label={`Target: ${KPI_LABELS[key]}`} hint="0 = not tracked">
            <input
              className="input"
              type="number"
              min={0}
              value={form.kpis[key]}
              onChange={(e) => setForm({ ...form, kpis: { ...form.kpis, [key]: Number(e.target.value) } })}
            />
          </Field>
        ))}
      </div>
    </Modal>
  )
}
