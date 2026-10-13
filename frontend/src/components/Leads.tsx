import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { isTeam, useUser } from '../lib/auth'
import { LEAD_STAGES, SOURCE_LABELS, STAGE_META, dateTime, money, plural, relative } from '../lib/format'
import { useToast } from '../lib/toast'
import type { Client, Content, Lead, LeadSource, LeadStage, OutreachKind } from '../lib/types'
import { useApi } from '../lib/useApi'
import { ContentEditor } from './ContentEditor'
import { Async, Badge, Button, Drawer, Empty, Field, Modal, SourceBadge, StageBadge } from './ui'

const OUTREACH_KINDS: { kind: OutreachKind; label: string }[] = [
  { kind: 'connection_note', label: 'Connection note' },
  { kind: 'follow_up', label: 'Follow-up' },
  { kind: 'meeting_request', label: 'Meeting request' },
]

export function LeadsBoard({ clientId, showClient }: { clientId?: number; showClient?: boolean }) {
  const user = useUser()
  const team = isTeam(user)
  const state = useApi(() => api.leads.pipeline(clientId), [clientId])
  const [selected, setSelected] = useState<Lead | null>(null)
  const [adding, setAdding] = useState(false)

  return (
    <Async state={state} label="Loading pipeline…">
      {(pipeline) => (
        <div className="stack">
          <div className="row wrap between">
            <div className="row wrap">
              <Badge tone="blue" plain>
                Open pipeline {money(pipeline.summary.open_value)}
              </Badge>
              <Badge tone="green" plain>
                Won {money(pipeline.summary.won_value)}
              </Badge>
              <span className="subtle">{plural(pipeline.summary.total, 'lead')}</span>
            </div>
            {team ? (
              <Button variant="primary" onClick={() => setAdding(true)}>
                Add lead
              </Button>
            ) : null}
          </div>
          {pipeline.summary.total === 0 ? (
            <div className="card">
              <Empty title="No leads yet">
                {team ? 'Add a lead or create one from a published post.' : 'Leads from your content will appear here.'}
              </Empty>
            </div>
          ) : (
            <div className="board">
              {pipeline.stages.map((column) => (
                <div className="board-col" key={column.stage}>
                  <div className="board-col-header">
                    <StageBadge stage={column.stage} />
                    <span className="subtle">
                      {column.leads.length} · {money(column.value)}
                    </span>
                  </div>
                  {column.leads.map((lead) => (
                    <button type="button" className="board-card" key={lead.id} onClick={() => setSelected(lead)}>
                      <span className="title">{lead.name}</span>
                      <span className="subtle">
                        {lead.title}
                        {lead.company ? ` · ${lead.company}` : ''}
                      </span>
                      <div className="row wrap">
                        <span className="chip">{SOURCE_LABELS[lead.source]}</span>
                        {lead.deal_value ? <span className="chip">{money(lead.deal_value)}</span> : null}
                        {showClient && lead.client_name ? <span className="chip">{lead.client_name}</span> : null}
                      </div>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
          {selected ? (
            <LeadDrawer
              key={selected.id}
              lead={selected}
              onClose={() => setSelected(null)}
              onChanged={(updated) => {
                setSelected(updated)
                state.reload()
              }}
            />
          ) : null}
          {adding ? (
            <NewLeadModal
              clientId={clientId}
              onClose={() => setAdding(false)}
              onCreated={() => {
                setAdding(false)
                state.reload()
              }}
            />
          ) : null}
        </div>
      )}
    </Async>
  )
}

export function LeadDrawer({
  lead,
  onClose,
  onChanged,
}: {
  lead: Lead
  onClose: () => void
  onChanged: (lead: Lead) => void
}) {
  const user = useUser()
  const team = isTeam(user)
  const toast = useToast()
  const [form, setForm] = useState({
    stage: lead.stage,
    score: lead.score,
    deal_value: lead.deal_value,
    notes: lead.notes,
  })
  const [saving, setSaving] = useState(false)
  const [kind, setKind] = useState<OutreachKind>('connection_note')
  const [outreach, setOutreach] = useState<{ text: string; subject: string; source: string } | null>(null)
  const [drafting, setDrafting] = useState(false)
  const [showPost, setShowPost] = useState(false)

  const dirty =
    form.stage !== lead.stage || form.score !== lead.score || form.deal_value !== lead.deal_value || form.notes !== lead.notes

  async function save() {
    setSaving(true)
    try {
      const updated = await api.leads.update(lead.id, team ? form : { notes: form.notes })
      toast.success('Lead updated')
      onChanged(updated)
    } catch (error) {
      toast.error(error)
    } finally {
      setSaving(false)
    }
  }

  async function draftOutreach() {
    setDrafting(true)
    try {
      const result = await api.ai.outreach(lead.id, kind)
      setOutreach({ text: result.message, subject: result.subject, source: result.source })
    } catch (error) {
      toast.error(error)
    } finally {
      setDrafting(false)
    }
  }

  async function copy() {
    if (!outreach) return
    const text = outreach.subject ? `Subject: ${outreach.subject}\n\n${outreach.text}` : outreach.text
    try {
      await navigator.clipboard.writeText(text)
      toast.success('Copied to clipboard')
    } catch {
      toast.error('Copy failed: select the text and copy it manually')
    }
  }

  return (
    <Drawer
      title={lead.name}
      onClose={onClose}
      subtitle={
        <div className="row wrap">
          <StageBadge stage={lead.stage} />
          <span className="muted">
            {lead.title}
            {lead.company ? ` at ${lead.company}` : ''}
          </span>
        </div>
      }
      footer={
        <Button variant="primary" disabled={!dirty} busy={saving} onClick={save}>
          Save
        </Button>
      }
    >
      <div className="stack">
        <div className="row wrap">
          <span className="chip">{SOURCE_LABELS[lead.source]}</span>
          {lead.client_name ? <span className="chip">{lead.client_name}</span> : null}
          {lead.email ? <a href={`mailto:${lead.email}`}>{lead.email}</a> : null}
          {lead.linkedin_url ? (
            <a href={lead.linkedin_url} target="_blank" rel="noreferrer">
              LinkedIn
            </a>
          ) : null}
          <span className="subtle">Added {relative(lead.created_at)}</span>
        </div>

        {lead.content_id ? (
          <div className="callout row between">
            <span>This lead came from one of your posts.</span>
            <Button size="sm" onClick={() => setShowPost(true)}>
              View post
            </Button>
          </div>
        ) : null}

        {team ? (
          <div className="form-grid">
            <Field label="Stage">
              <select className="select" value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value as LeadStage })}>
                {LEAD_STAGES.map((stage) => (
                  <option key={stage} value={stage}>
                    {STAGE_META[stage].label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Deal value ($)">
              <input
                className="input"
                type="number"
                min={0}
                value={form.deal_value}
                onChange={(e) => setForm({ ...form, deal_value: Number(e.target.value) })}
              />
            </Field>
            <Field label="Score (0-100)">
              <input
                className="input"
                type="number"
                min={0}
                max={100}
                value={form.score}
                onChange={(e) => setForm({ ...form, score: Number(e.target.value) })}
              />
            </Field>
            <Field label="Stage changed">
              <input className="input" readOnly value={dateTime(lead.stage_changed_at)} />
            </Field>
          </div>
        ) : (
          <div className="row wrap">
            <span className="muted">Deal value</span>
            <strong>{money(lead.deal_value)}</strong>
          </div>
        )}

        <Field label="Notes">
          <textarea className="textarea" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </Field>

        {team ? (
          <div className="card card-body stack tight">
            <div className="row between">
              <h3>AI outreach</h3>
              {outreach ? <SourceBadge source={outreach.source} /> : null}
            </div>
            <div className="row wrap">
              <div className="segmented" role="tablist">
                {OUTREACH_KINDS.map((option) => (
                  <button
                    key={option.kind}
                    type="button"
                    className={kind === option.kind ? 'active' : ''}
                    onClick={() => setKind(option.kind)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <Button size="sm" variant="primary" busy={drafting} onClick={draftOutreach}>
                Draft message
              </Button>
            </div>
            {outreach ? (
              <>
                {outreach.subject ? <div className="subtle">Subject: {outreach.subject}</div> : null}
                <textarea
                  className="textarea"
                  style={{ minHeight: 160 }}
                  value={outreach.text}
                  onChange={(e) => setOutreach({ ...outreach, text: e.target.value })}
                />
                <div className="row">
                  <Button size="sm" onClick={copy}>
                    Copy
                  </Button>
                  <span className="subtle">{outreach.text.length} characters</span>
                </div>
              </>
            ) : null}
          </div>
        ) : null}
      </div>
      {showPost && lead.content_id ? (
        <ContentEditor contentId={lead.content_id} onClose={() => setShowPost(false)} />
      ) : null}
    </Drawer>
  )
}

function NewLeadModal({
  clientId,
  onClose,
  onCreated,
}: {
  clientId?: number
  onClose: () => void
  onCreated: () => void
}) {
  const toast = useToast()
  const [clients, setClients] = useState<Client[]>([])
  const [posts, setPosts] = useState<Content[]>([])
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    client_id: clientId ?? 0,
    name: '',
    title: '',
    company: '',
    email: '',
    source: 'inbound' as LeadSource,
    stage: 'new' as LeadStage,
    deal_value: 0,
    content_id: 0,
  })

  useEffect(() => {
    if (clientId === undefined) api.clients.list({ status: 'active' }).then(setClients).catch(toast.error)
  }, [clientId, toast])

  useEffect(() => {
    if (!form.client_id) return
    api.content
      .list({ client_id: form.client_id, status: 'published' })
      .then(setPosts)
      .catch(() => setPosts([]))
  }, [form.client_id])

  async function submit() {
    setSaving(true)
    try {
      await api.leads.create({
        ...form,
        content_id: form.content_id || null,
        source: form.content_id ? 'content' : form.source,
      })
      toast.success(`${form.name} added to the pipeline`)
      onCreated()
    } catch (error) {
      toast.error(error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title="Add lead"
      onClose={onClose}
      footer={
        <Button variant="primary" busy={saving} disabled={!form.client_id || !form.name.trim()} onClick={submit}>
          Add lead
        </Button>
      }
    >
      <div className="form-grid">
        {clientId === undefined ? (
          <Field label="Client" full>
            <select
              className="select"
              value={form.client_id}
              onChange={(e) => setForm({ ...form, client_id: Number(e.target.value), content_id: 0 })}
            >
              <option value={0}>Choose a client…</option>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name} · {client.company}
                </option>
              ))}
            </select>
          </Field>
        ) : null}
        <Field label="Name">
          <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Title">
          <input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="Company">
          <input className="input" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
        </Field>
        <Field label="Email">
          <input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Source post" hint="Attributes the lead to content" full>
          <select
            className="select"
            value={form.content_id}
            onChange={(e) => setForm({ ...form, content_id: Number(e.target.value) })}
            disabled={!posts.length}
          >
            <option value={0}>{posts.length ? 'None' : 'No published posts'}</option>
            {posts.map((post) => (
              <option key={post.id} value={post.id}>
                {post.title}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Source">
          <select
            className="select"
            value={form.content_id ? 'content' : form.source}
            disabled={Boolean(form.content_id)}
            onChange={(e) => setForm({ ...form, source: e.target.value as LeadSource })}
          >
            {(Object.keys(SOURCE_LABELS) as LeadSource[]).map((source) => (
              <option key={source} value={source}>
                {SOURCE_LABELS[source]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Deal value ($)">
          <input
            className="input"
            type="number"
            min={0}
            value={form.deal_value}
            onChange={(e) => setForm({ ...form, deal_value: Number(e.target.value) })}
          />
        </Field>
      </div>
    </Modal>
  )
}
