import { useState } from 'react'
import { Async, Button, Card, Field, PageHeader } from '../../components/ui'
import { api } from '../../lib/api'
import { useUser } from '../../lib/auth'
import { useToast } from '../../lib/toast'
import type { Client } from '../../lib/types'
import { useApi } from '../../lib/useApi'

const lines = (text: string) => text.split('\n').map((l) => l.trim()).filter(Boolean)

function toForm(client: Client) {
  return {
    brand_voice: client.brand_voice,
    tone_tags: client.tone_tags.join(', '),
    target_audience: client.target_audience,
    content_pillars: client.content_pillars.join('\n'),
    topics_to_avoid: client.topics_to_avoid,
    goals: client.goals.join('\n'),
    auto_approve_hours: client.auto_approve_hours,
  }
}

export function Preferences() {
  const user = useUser()
  const state = useApi(() => api.clients.get(user.client_id!), [user.client_id])
  return (
    <>
      <PageHeader
        eyebrow="Preferences"
        title="How you sound, and how we work"
        description="Changes apply to every new draft the team writes for you."
      />
      <Async state={state}>{(client) => <PreferencesForm client={client} onSaved={(c) => state.setData(c)} />}</Async>
    </>
  )
}

function PreferencesForm({ client, onSaved }: { client: Client; onSaved: (client: Client) => void }) {
  const toast = useToast()
  const [form, setForm] = useState(() => toForm(client))
  const [saving, setSaving] = useState(false)
  const set = (patch: Partial<ReturnType<typeof toForm>>) => setForm((current) => ({ ...current, ...patch }))


  async function save() {
    setSaving(true)
    try {
      const updated = await api.clients.update(client.id, {
        brand_voice: form.brand_voice,
        tone_tags: form.tone_tags.split(',').map((t) => t.trim()).filter(Boolean),
        target_audience: form.target_audience,
        content_pillars: lines(form.content_pillars),
        topics_to_avoid: form.topics_to_avoid,
        goals: lines(form.goals),
        auto_approve_hours: form.auto_approve_hours,
      })
      onSaved(updated)
      toast.success('Preferences saved')
    } catch (error) {
      toast.error(error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="stack">
      <Card title="Your voice">
        <div className="form-grid">
          <Field label="How you like to sound" full>
            <textarea className="textarea" value={form.brand_voice} onChange={(e) => set({ brand_voice: e.target.value })} />
          </Field>
          <Field label="Tone" hint="A few words, comma separated">
            <input className="input" value={form.tone_tags} onChange={(e) => set({ tone_tags: e.target.value })} />
          </Field>
          <Field label="Who you want to reach">
            <input className="input" value={form.target_audience} onChange={(e) => set({ target_audience: e.target.value })} />
          </Field>
          <Field label="Topics you want to be known for" hint="One per line">
            <textarea className="textarea" value={form.content_pillars} onChange={(e) => set({ content_pillars: e.target.value })} />
          </Field>
          <Field label="Goals" hint="One per line">
            <textarea className="textarea" value={form.goals} onChange={(e) => set({ goals: e.target.value })} />
          </Field>
          <Field label="Never post about" full>
            <input className="input" value={form.topics_to_avoid} onChange={(e) => set({ topics_to_avoid: e.target.value })} />
          </Field>
        </div>
      </Card>
      <Card title="Auto-approve" subtitle="Busy week? Let posts go out if you haven't replied in time.">
        <div className="stack tight" style={{ maxWidth: 420 }}>
          <select
            className="select"
            value={form.auto_approve_hours}
            onChange={(e) => set({ auto_approve_hours: Number(e.target.value) })}
            aria-label="Auto-approve window"
          >
            <option value={0}>Off: always wait for me</option>
            <option value={24}>Approve automatically after 24 hours</option>
            <option value={48}>Approve automatically after 48 hours</option>
            <option value={72}>Approve automatically after 72 hours</option>
            {![0, 24, 48, 72].includes(form.auto_approve_hours) ? (
              <option value={form.auto_approve_hours}>After {form.auto_approve_hours} hours</option>
            ) : null}
          </select>
          <span className="subtle">You can still request changes on a scheduled post before it goes out.</span>
        </div>
      </Card>
      <div>
        <Button variant="primary" size="lg" busy={saving} onClick={save}>
          Save preferences
        </Button>
      </div>
    </div>
  )
}
