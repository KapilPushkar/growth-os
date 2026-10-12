import { useEffect, useState } from 'react'
import { Button, Card, Field } from '../../../components/ui'
import { api } from '../../../lib/api'
import { CHANNEL_LABELS, CHANNELS } from '../../../lib/format'
import { useToast } from '../../../lib/toast'
import type { Channel, Client, ClientStatus, User } from '../../../lib/types'

function toForm(client: Client) {
  return {
    name: client.name,
    title: client.title,
    company: client.company,
    industry: client.industry,
    website: client.website,
    plan: client.plan,
    status: client.status,
    account_manager_id: client.account_manager_id ?? 0,
    positioning: client.positioning,
    brand_voice: client.brand_voice,
    tone_tags: client.tone_tags.join(', '),
    target_audience: client.target_audience,
    content_pillars: client.content_pillars.join('\n'),
    topics_to_avoid: client.topics_to_avoid,
    goals: client.goals.join('\n'),
    channels: client.channels,
    posting_cadence: client.posting_cadence,
    auto_approve_hours: client.auto_approve_hours,
  }
}

const lines = (text: string) => text.split('\n').map((l) => l.trim()).filter(Boolean)

export function BrandTab({ client, onSaved }: { client: Client; onSaved: (client: Client) => void }) {
  const toast = useToast()
  const [form, setForm] = useState(() => toForm(client))
  const [team, setTeam] = useState<User[]>([])
  const [saving, setSaving] = useState(false)
  const set = (patch: Partial<ReturnType<typeof toForm>>) => setForm((current) => ({ ...current, ...patch }))

  useEffect(() => {
    api.users().then((users) => setTeam(users.filter((u) => u.role !== 'client'))).catch(() => setTeam([]))
  }, [])

  async function save() {
    setSaving(true)
    try {
      const updated = await api.clients.update(client.id, {
        ...form,
        account_manager_id: form.account_manager_id || null,
        tone_tags: form.tone_tags.split(',').map((t) => t.trim()).filter(Boolean),
        content_pillars: lines(form.content_pillars),
        goals: lines(form.goals),
      })
      onSaved(updated)
      toast.success('Brand profile saved. New drafts will use it.')
    } catch (error) {
      toast.error(error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="stack">
      <Card title="Brand profile" subtitle="Every AI prompt starts from this brief, so keep it specific.">
        <div className="form-grid">
          <Field label="Positioning" full>
            <textarea className="textarea" value={form.positioning} onChange={(e) => set({ positioning: e.target.value })} />
          </Field>
          <Field label="Brand voice" full>
            <textarea className="textarea" value={form.brand_voice} onChange={(e) => set({ brand_voice: e.target.value })} />
          </Field>
          <Field label="Tone tags" hint="Comma separated">
            <input className="input" value={form.tone_tags} onChange={(e) => set({ tone_tags: e.target.value })} />
          </Field>
          <Field label="Target audience">
            <input className="input" value={form.target_audience} onChange={(e) => set({ target_audience: e.target.value })} />
          </Field>
          <Field label="Content pillars" hint="One per line">
            <textarea className="textarea" value={form.content_pillars} onChange={(e) => set({ content_pillars: e.target.value })} />
          </Field>
          <Field label="Goals" hint="One per line">
            <textarea className="textarea" value={form.goals} onChange={(e) => set({ goals: e.target.value })} />
          </Field>
          <Field label="Topics to avoid" full>
            <input className="input" value={form.topics_to_avoid} onChange={(e) => set({ topics_to_avoid: e.target.value })} />
          </Field>
        </div>
      </Card>

      <Card title="Channels, cadence and approvals">
        <div className="stack">
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
                        : form.channels.filter((c: Channel) => c !== channel),
                    })
                  }
                />
                {CHANNEL_LABELS[channel]}
              </label>
            ))}
          </div>
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
            <Field label="Auto-approve after (hours)" hint="0 turns auto-approve off">
              <input
                className="input"
                type="number"
                min={0}
                max={720}
                value={form.auto_approve_hours}
                onChange={(e) => set({ auto_approve_hours: Number(e.target.value) })}
              />
            </Field>
          </div>
        </div>
      </Card>

      <Card title="Account">
        <div className="form-grid">
          <Field label="Name">
            <input className="input" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          </Field>
          <Field label="Title">
            <input className="input" value={form.title} onChange={(e) => set({ title: e.target.value })} />
          </Field>
          <Field label="Company">
            <input className="input" value={form.company} onChange={(e) => set({ company: e.target.value })} />
          </Field>
          <Field label="Industry">
            <input className="input" value={form.industry} onChange={(e) => set({ industry: e.target.value })} />
          </Field>
          <Field label="Website">
            <input className="input" value={form.website} onChange={(e) => set({ website: e.target.value })} />
          </Field>
          <Field label="Plan">
            <select className="select" value={form.plan} onChange={(e) => set({ plan: e.target.value })}>
              <option value="starter">Starter</option>
              <option value="growth">Growth</option>
              <option value="scale">Scale</option>
            </select>
          </Field>
          <Field label="Status">
            <select className="select" value={form.status} onChange={(e) => set({ status: e.target.value as ClientStatus })}>
              <option value="onboarding">Onboarding</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
            </select>
          </Field>
          <Field label="Account manager">
            <select
              className="select"
              value={form.account_manager_id}
              onChange={(e) => set({ account_manager_id: Number(e.target.value) })}
            >
              <option value={0}>Unassigned</option>
              {team.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </Card>

      <div>
        <Button variant="primary" size="lg" busy={saving} onClick={save}>
          Save profile
        </Button>
      </div>
    </div>
  )
}
