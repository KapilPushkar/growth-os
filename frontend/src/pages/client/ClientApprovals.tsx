import { useState } from 'react'
import { PostPreview } from '../../components/PostPreview'
import { Async, Badge, Button, Card, Empty, PageHeader } from '../../components/ui'
import { api } from '../../lib/api'
import { useUser } from '../../lib/auth'
import { CHANNEL_LABELS, relative, waited } from '../../lib/format'
import { useToast } from '../../lib/toast'
import type { QueueItem } from '../../lib/types'
import { useApi } from '../../lib/useApi'

export function ClientApprovals() {
  const toast = useToast()
  const state = useApi(() => api.approvals(), [])
  const [approvingAll, setApprovingAll] = useState(false)

  async function approveAll(items: QueueItem[]) {
    if (!window.confirm(`Approve all ${items.length} posts?`)) return
    setApprovingAll(true)
    try {
      const result = await api.content.bulk(
        items.map((item) => item.id),
        'approve',
      )
      if (result.errors.length) toast.error(`${result.errors.length} could not be approved: ${result.errors[0].detail}`)
      toast.success(`Approved ${result.done.length} post${result.done.length === 1 ? '' : 's'}`)
      state.reload()
    } catch (error) {
      toast.error(error)
    } finally {
      setApprovingAll(false)
    }
  }

  return (
    <Async state={state} label="Loading your approvals…">
      {(queues) => (
        <div className="stack">
          <PageHeader
            eyebrow="Approvals"
            title={
              queues.client_review.length
                ? `${queues.client_review.length} post${queues.client_review.length === 1 ? '' : 's'} to review`
                : "You're all caught up"
            }
            description="Each post is shown as it will appear. Approve it, or tell us what to change."
            actions={
              queues.client_review.length > 1 ? (
                <Button variant="primary" busy={approvingAll} onClick={() => void approveAll(queues.client_review)}>
                  Approve all
                </Button>
              ) : null
            }
          />
          {queues.client_review.length === 0 ? (
            <div className="card">
              <Empty title="Nothing needs your approval">New drafts from the team will appear here.</Empty>
            </div>
          ) : (
            queues.client_review.map((item) => <ApprovalCard key={item.id} item={item} onDone={state.reload} />)
          )}
          {queues.changes_requested.length ? (
            <Card title="Changes you requested" subtitle="The team is revising these" bodyless>
              <ul className="list">
                {queues.changes_requested.map((item) => (
                  <li key={item.id}>
                    <div className="grow">
                      <strong>{item.title}</strong>
                      <div className="subtle">
                        {CHANNEL_LABELS[item.channel]} · requested {relative(item.status_changed_at)}
                      </div>
                    </div>
                    <Badge tone="red">In revision</Badge>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}
        </div>
      )}
    </Async>
  )
}

function ApprovalCard({ item, onDone }: { item: QueueItem; onDone: () => void }) {
  const user = useUser()
  const toast = useToast()
  const [mode, setMode] = useState<'idle' | 'changes' | 'comment'>('idle')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  async function act(action: 'approve' | 'request_changes' | 'comment') {
    if (action !== 'approve' && !note.trim()) {
      toast.error(action === 'comment' ? 'Write a comment first' : 'Tell us what to change')
      return
    }
    setBusy(true)
    try {
      await api.content.transition(item.id, action, action === 'approve' ? undefined : { note })
      toast.success(
        action === 'approve' ? 'Approved. We will schedule it.' : action === 'comment' ? 'Comment sent' : 'Sent back with your notes',
      )
      setNote('')
      setMode('idle')
      onDone()
    } catch (error) {
      toast.error(error)
    } finally {
      setBusy(false)
    }
  }

  const author = user.client ?? { name: user.name, title: '', company: '' }
  return (
    <Card
      title={item.title}
      subtitle={`${CHANNEL_LABELS[item.channel]} · waiting ${waited(item.waiting_hours)}${
        item.auto_approve_in_hours !== null ? ` · auto-approves in ${waited(item.auto_approve_in_hours)}` : ''
      }`}
    >
      <div className="grid main-side">
        <PostPreview channel={item.channel} body={item.body} hashtags={item.hashtags} author={author} />
        <div className="stack">
          <Button variant="primary" size="lg" busy={busy && mode === 'idle'} onClick={() => void act('approve')}>
            Approve
          </Button>
          <div className="row">
            <Button className="grow" variant={mode === 'changes' ? 'danger' : 'default'} onClick={() => setMode(mode === 'changes' ? 'idle' : 'changes')}>
              Request changes
            </Button>
            <Button className="grow" onClick={() => setMode(mode === 'comment' ? 'idle' : 'comment')}>
              Comment
            </Button>
          </div>
          {mode !== 'idle' ? (
            <div className="stack tight">
              <textarea
                className="textarea"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={mode === 'changes' ? 'What should we change? (required)' : 'Your comment'}
                autoFocus
              />
              <Button
                variant={mode === 'changes' ? 'danger' : 'default'}
                busy={busy}
                disabled={!note.trim()}
                onClick={() => void act(mode === 'changes' ? 'request_changes' : 'comment')}
              >
                {mode === 'changes' ? 'Send back with notes' : 'Send comment'}
              </Button>
            </div>
          ) : null}
          {item.pillar ? <span className="subtle">Pillar: {item.pillar}</span> : null}
        </div>
      </div>
    </Card>
  )
}
