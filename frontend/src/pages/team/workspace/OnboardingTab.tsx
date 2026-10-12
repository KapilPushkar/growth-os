import { useState } from 'react'
import { Badge, Card, Progress } from '../../../components/ui'
import { api } from '../../../lib/api'
import { date } from '../../../lib/format'
import { useToast } from '../../../lib/toast'
import type { Client } from '../../../lib/types'

const HINTS: Record<string, string> = {
  intake: 'Kick-off call done; positioning, voice, audience, pillars and goals captured in the brand profile.',
  access: 'Access to LinkedIn/X, newsletter tool, website analytics and CRM confirmed.',
  strategy: 'Content pillars, ideal customer profile and channel plan agreed with the client.',
  first_batch: 'First batch of drafts reviewed and approved by the client.',
  launch: 'Calendar scheduled and reporting baseline captured. The client goes live.',
}

export function OnboardingTab({ client, onChanged }: { client: Client; onChanged: (client: Client) => void }) {
  const toast = useToast()
  const [busy, setBusy] = useState<string | null>(null)

  async function toggle(step: string, done: boolean) {
    setBusy(step)
    try {
      const updated = await api.clients.onboarding(client.id, step, done)
      onChanged(updated)
      if (updated.status === 'active' && client.status === 'onboarding') {
        toast.success(`${client.name} is live!`)
      } else {
        toast.success(done ? 'Step completed' : 'Step reopened')
      }
    } catch (error) {
      toast.error(error)
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card
      title="Onboarding checklist"
      subtitle="Completing all five steps takes the client live and starts their reporting."
      actions={client.status === 'active' ? <Badge tone="green">Live since {date(client.start_date)}</Badge> : null}
    >
      <div className="stack">
        <div className="row">
          <div className="grow">
            <Progress value={client.onboarding_pct} label="Onboarding progress" />
          </div>
          <strong>{client.onboarding_pct}%</strong>
        </div>
        <ul className="list card">
          {client.onboarding.map((step, index) => (
            <li key={step.key}>
              <label className="checkbox" style={{ alignItems: 'flex-start', gap: 12 }}>
                <input
                  type="checkbox"
                  checked={step.done}
                  disabled={busy !== null}
                  onChange={(e) => void toggle(step.key, e.target.checked)}
                  style={{ marginTop: 4, width: 16, height: 16 }}
                />
                <span className="stack tight" style={{ gap: 2 }}>
                  <strong>
                    {index + 1}. {step.label}
                  </strong>
                  <span className="muted">{HINTS[step.key]}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  )
}
