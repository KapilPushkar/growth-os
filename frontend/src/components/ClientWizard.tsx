import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { CHANNEL_LABELS, CHANNELS } from '../lib/format'
import { navigate } from '../lib/router'
import { useToast } from '../lib/toast'
import type { Channel, Client, User } from '../lib/types'
import { Button, Field, Modal } from './ui'

const STEPS = ['Basics', 'Brand profile', 'Channels & approvals']

const lines = (text: string) => text.split('\n').map((l) => l.trim()).filter(Boolean)
const commas = (text: string) => text.split(',').map((t) => t.trim()).filter(Boolean)

export function ClientWizard({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const toast = useToast()
  const [step, setStep] = useState(0)
  const [saving, setSaving] = useState(false)
  const [team, setTeam] = useState<User[]>([])
  const [created, setCreated] = useState<{ client: Client; login: { email: string; temp_password: string } | null } | null>(null)
  const [form, setForm] = useState({
    name: '',
    title: '',
    email: '',
    company: '',
    industry: '',
    website: '',
    plan: 'growth',
    account_manager_id: 0,
    create_login: true,
    positioning: '',
    brand_voice: '',
    tone_tags: '',
    target_audience: '',
    content_pillars: '',
    topics_to_avoid: '',
    goals: '',
    channels: ['linkedin'] as Channel[],
    posting_cadence: 3,
    auto_approve_hours: 0,
  })
  const set = (patch: Partial<typeof form>) => setForm((current) => ({ ...current, ...patch }))

  useEffect(() => {
    api.users('strategist').then(setTeam).catch(() => setTeam([]))
  }, [])

  const basicsValid = form.name.trim() && form.company.trim() && (!form.create_login || /\S+@\S+\.\S+/.test(form.email))
  const canContinue = step === 0 ? Boolean(basicsValid) : step === 2 ? form.channels.length > 0 : true

  async function submit() {
    setSaving(true)
    try {
      const result = await api.clients.create({
        name: form.name,
        title: form.title,
        email: form.email || null,
        company: form.company,
        industry: form.industry,
        website: form.website,
        plan: form.plan,
        account_manager_id: form.account_manager_id || null,
        create_login: form.create_login,
        positioning: form.positioning,
        brand_voice: form.brand_voice,
        tone_tags: commas(form.tone_tags),
        target_audience: form.target_audience,
        content_pillars: lines(form.content_pillars),
        topics_to_avoid: form.topics_to_avoid,
        goals: lines(form.goals),
        channels: form.channels,
        posting_cadence: form.posting_cadence,
        auto_approve_hours: form.auto_approve_hours,
      })
      setCreated(result)
      toast.success(`${result.client.name} added. Onboarding has started.`)
      onCreated()
    } catch (error) {
      toast.error(error)
    } finally {
      setSaving(false)
    }
  }

  if (created) {
    return (
      <Modal
        title="Client created"
        onClose={onClose}
        footer={
          <Button variant="primary" onClick={() => navigate(`/clients/${created.client.id}/onboarding`)}>
            Open onboarding
          </Button>
        }
      >
        <div className="stack">
          <p>
            <strong>{created.client.name}</strong> ({created.client.company}) is in onboarding.
          </p>
          {created.login ? (
            <div className="card card-body stack tight">
              <h3>Client login</h3>
              <p className="muted">Share these with the client securely. The password is shown only once.</p>
              <div className="row between">
                <span className="muted">Email</span>
                <strong>{created.login.email}</strong>
              </div>
              <div className="row between">
                <span className="muted">Temporary password</span>
                <code style={{ fontSize: 15 }}>{created.login.temp_password}</code>
              </div>
              <div>
                <Button
                  size="sm"
                  onClick={() =>
                    navigator.clipboard
                      .writeText(`${created.login!.email}\n${created.login!.temp_password}`)
                      .then(() => toast.success('Login copied'))
                      .catch(() => toast.error('Copy failed'))
                  }
                >
                  Copy login
                </Button>
              </div>
            </div>
          ) : (
            <p className="muted">No client login was created.</p>
          )}
        </div>
      </Modal>
    )
  }

  return (
    <Modal
      title={`New client · ${STEPS[step]}`}
      onClose={onClose}
      footer={
        <>
          {step > 0 ? <Button onClick={() => setStep(step - 1)}>Back</Button> : null}
          <span className="grow" />
          {step < STEPS.length - 1 ? (
            <Button variant="primary" disabled={!canContinue} onClick={() => setStep(step + 1)}>
              Continue
            </Button>
          ) : (
            <Button variant="primary" disabled={!canContinue} busy={saving} onClick={submit}>
              Create client
            </Button>
          )}
        </>
      }
    >
      <div className="steps" aria-hidden>
        {STEPS.map((label, i) => (
          <span key={label} className={i <= step ? 'on' : ''} />
        ))}
      </div>

      {step === 0 ? (
        <div className="form-grid">
          <Field label="Founder / executive name">
            <input className="input" value={form.name} onChange={(e) => set({ name: e.target.value })} autoFocus />
          </Field>
          <Field label="Title">
            <input className="input" value={form.title} onChange={(e) => set({ title: e.target.value })} placeholder="Founder & CEO" />
          </Field>
          <Field label="Company">
            <input className="input" value={form.company} onChange={(e) => set({ company: e.target.value })} />
          </Field>
          <Field label="Industry">
            <input className="input" value={form.industry} onChange={(e) => set({ industry: e.target.value })} />
          </Field>
          <Field label="Email" hint={form.create_login ? 'Used as their login' : undefined}>
            <input className="input" type="email" value={form.email} onChange={(e) => set({ email: e.target.value })} />
          </Field>
          <Field label="Website">
            <input className="input" value={form.website} onChange={(e) => set({ website: e.target.value })} placeholder="https://" />
          </Field>
          <Field label="Plan">
            <select className="select" value={form.plan} onChange={(e) => set({ plan: e.target.value })}>
              <option value="starter">Starter</option>
              <option value="growth">Growth</option>
              <option value="scale">Scale</option>
            </select>
          </Field>
          <Field label="Account manager">
            <select
              className="select"
              value={form.account_manager_id}
              onChange={(e) => set({ account_manager_id: Number(e.target.value) })}
            >
              <option value={0}>Assign to me</option>
              {team.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.name}
                </option>
              ))}
            </select>
          </Field>
          <label className="checkbox full">
            <input type="checkbox" checked={form.create_login} onChange={(e) => set({ create_login: e.target.checked })} />
            Create a client login (temporary password shown once)
          </label>
        </div>
      ) : null}

      {step === 1 ? (
        <div className="form-grid">
          <Field label="Positioning" full>
            <textarea className="textarea" value={form.positioning} onChange={(e) => set({ positioning: e.target.value })} placeholder="What the company does, for whom, and why it matters" />
          </Field>
          <Field label="Brand voice" full>
            <textarea className="textarea" value={form.brand_voice} onChange={(e) => set({ brand_voice: e.target.value })} placeholder="How they sound: e.g. direct, numbers-first, no hype" />
          </Field>
          <Field label="Tone tags" hint="Comma separated">
            <input className="input" value={form.tone_tags} onChange={(e) => set({ tone_tags: e.target.value })} placeholder="direct, warm, data-driven" />
          </Field>
          <Field label="Target audience">
            <input className="input" value={form.target_audience} onChange={(e) => set({ target_audience: e.target.value })} />
          </Field>
          <Field label="Content pillars" hint="One per line (3-4 works best)">
            <textarea className="textarea" value={form.content_pillars} onChange={(e) => set({ content_pillars: e.target.value })} />
          </Field>
          <Field label="Goals" hint="One per line">
            <textarea className="textarea" value={form.goals} onChange={(e) => set({ goals: e.target.value })} />
          </Field>
          <Field label="Topics to avoid" full>
            <input className="input" value={form.topics_to_avoid} onChange={(e) => set({ topics_to_avoid: e.target.value })} />
          </Field>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="stack">
          <Field label="Channels">
            <div className="row wrap" style={{ gap: 16 }}>
              {CHANNELS.map((channel) => (
                <label className="checkbox" key={channel}>
                  <input
                    type="checkbox"
                    checked={form.channels.includes(channel)}
                    onChange={(e) =>
                      set({
                        channels: e.target.checked
                          ? [...form.channels, channel]
                          : form.channels.filter((c) => c !== channel),
                      })
                    }
                  />
                  {CHANNEL_LABELS[channel]}
                </label>
              ))}
            </div>
          </Field>
          <div className="form-grid">
            <Field label="Posting cadence (posts per week)">
              <input
                className="input"
                type="number"
                min={0}
                max={21}
                value={form.posting_cadence}
                onChange={(e) => set({ posting_cadence: Number(e.target.value) })}
              />
            </Field>
            <Field label="Auto-approve" hint="Approve automatically if the client hasn't responded">
              <select
                className="select"
                value={form.auto_approve_hours}
                onChange={(e) => set({ auto_approve_hours: Number(e.target.value) })}
              >
                <option value={0}>Off: always wait for the client</option>
                <option value={24}>After 24 hours</option>
                <option value={48}>After 48 hours</option>
                <option value={72}>After 72 hours</option>
              </select>
            </Field>
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
