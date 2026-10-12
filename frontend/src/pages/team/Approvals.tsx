import { useState } from 'react'
import { ContentEditor } from '../../components/ContentEditor'
import { Async, Badge, Card, Empty, PageHeader } from '../../components/ui'
import { api } from '../../lib/api'
import { CHANNEL_LABELS, waited } from '../../lib/format'
import { useLocation } from '../../lib/router'
import type { QueueItem } from '../../lib/types'
import { useApi } from '../../lib/useApi'
import { STUCK_HOURS } from '../constants'

const QUEUES = [
  { key: 'internal_review', title: 'Internal review', hint: 'Drafts waiting on the team' },
  { key: 'client_review', title: 'With client', hint: 'Waiting for the client to approve' },
  { key: 'changes_requested', title: 'Changes requested', hint: 'Client feedback to action' },
] as const

export function Approvals() {
  const { query } = useLocation()
  const [clientId, setClientId] = useState<number | ''>(query.get('client') ? Number(query.get('client')) : '')
  const [openId, setOpenId] = useState<number | null>(null)
  const clients = useApi(() => api.clients.list({ status: 'active' }), [])
  const state = useApi(() => api.approvals(clientId || undefined), [clientId])

  return (
    <>
      <PageHeader
        eyebrow="Approval layer"
        title="Approval queues"
        description="Everything waiting on someone, oldest first. Auto-approve fires once a client's window passes."
        actions={
          <select
            className="select"
            style={{ width: 220 }}
            value={clientId}
            onChange={(e) => setClientId(e.target.value ? Number(e.target.value) : '')}
            aria-label="Filter by client"
          >
            <option value="">All clients</option>
            {(clients.data ?? []).map((client) => (
              <option key={client.id} value={client.id}>
                {client.name}
              </option>
            ))}
          </select>
        }
      />
      <Async state={state} label="Loading queues…">
        {(queues) => (
          <div className="grid cols-3">
            {QUEUES.map((queue) => (
              <Card key={queue.key} title={`${queue.title} · ${queues[queue.key].length}`} subtitle={queue.hint} bodyless>
                {queues[queue.key].length ? (
                  <ul className="list">
                    {queues[queue.key].map((item) => (
                      <QueueRow key={item.id} item={item} onOpen={() => setOpenId(item.id)} />
                    ))}
                  </ul>
                ) : (
                  <Empty compact title="All clear" />
                )}
              </Card>
            ))}
          </div>
        )}
      </Async>
      {openId !== null ? <ContentEditor contentId={openId} onClose={() => setOpenId(null)} onChanged={state.reload} /> : null}
    </>
  )
}

function QueueRow({ item, onOpen }: { item: QueueItem; onOpen: () => void }) {
  const stuck = item.status === 'client_review' && item.waiting_hours >= STUCK_HOURS
  return (
    <li className="clickable" onClick={onOpen}>
      <div className="grow stack tight" style={{ gap: 4 }}>
        <strong>{item.title || 'Untitled'}</strong>
        <span className="subtle">
          {item.client.name} · {CHANNEL_LABELS[item.channel]}
        </span>
        {item.auto_approve_in_hours !== null ? (
          <span className="subtle">Auto-approves in {waited(item.auto_approve_in_hours)}</span>
        ) : null}
      </div>
      <Badge tone={stuck ? 'red' : 'neutral'} plain>
        waiting {waited(item.waiting_hours)}
      </Badge>
    </li>
  )
}
