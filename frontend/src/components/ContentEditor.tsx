import { useState } from 'react'
import { api } from '../lib/api'
import { isTeam, useUser } from '../lib/auth'
import {
  ACTION_LABELS,
  CHANNEL_LABELS,
  CHANNELS,
  EVENT_LABELS,
  STATUS_META,
  dateTime,
  humanize,
  num,
  relative,
  toLocalInput,
} from '../lib/format'
import { useToast } from '../lib/toast'
import type { Action, Channel, ContentDetail, ContentStatus } from '../lib/types'
import { useApi } from '../lib/useApi'
import { PostPreview } from './PostPreview'
import { Badge, Button, Drawer, ErrorState, Field, Loading, SimulatedBadge, SourceBadge, StatusBadge } from './ui'

// Actions shown as primary buttons; the rest are secondary.
const PRIMARY: Action[] = ['approve', 'send_to_client', 'publish', 'submit']

function defaultSlot(): string {
  const slot = new Date()
  slot.setDate(slot.getDate() + 1)
  slot.setHours(9, 0, 0, 0)
  return toLocalInput(slot)
}

export function ContentEditor({
  contentId,
  onClose,
  onChanged,
}: {
  contentId: number
  onClose: () => void
  onChanged?: () => void
}) {
  const state = useApi(() => api.content.get(contentId), [contentId])

  if (!state.data) {
    return (
      <Drawer title="Content" onClose={onClose}>
        {state.error ? <ErrorState message={state.error} onRetry={state.reload} /> : <Loading />}
      </Drawer>
    )
  }
  // Re-key on every saved change so the form starts from the latest version.
  return (
    <EditorBody
      key={`${state.data.id}:${state.data.updated_at}`}
      piece={state.data}
      onUpdated={state.setData}
      onClose={onClose}
      onChanged={onChanged}
    />
  )
}

function EditorBody({
  piece,
  onUpdated,
  onClose,
  onChanged,
}: {
  piece: ContentDetail
  onUpdated: (piece: ContentDetail) => void
  onClose: () => void
  onChanged?: () => void
}) {
  const user = useUser()
  const team = isTeam(user)
  const toast = useToast()
  const [draft, setDraft] = useState(() => ({
    title: piece.title,
    body: piece.body,
    hashtags: piece.hashtags.join(' '),
    pillar: piece.pillar,
    target_keyword: piece.target_keyword,
  }))
  const [note, setNote] = useState('')
  const [comment, setComment] = useState('')
  const [slot, setSlot] = useState(defaultSlot)
  const [repurposeTo, setRepurposeTo] = useState<Channel>(piece.channel === 'newsletter' ? 'linkedin' : 'newsletter')
  const [busy, setBusy] = useState<string | null>(null)

  const hashtags = draft.hashtags.split(/[\s,]+/).filter(Boolean).map((t) => (t.startsWith('#') ? t : `#${t}`))
  const dirty =
    draft.title !== piece.title ||
    draft.body !== piece.body ||
    hashtags.join(' ') !== piece.hashtags.join(' ') ||
    draft.pillar !== piece.pillar ||
    draft.target_keyword !== piece.target_keyword
  const editable = team && piece.status !== 'published'
  const actions = piece.allowed_actions.filter((a) => a !== 'comment')

  async function run(key: string, work: () => Promise<ContentDetail | void>, success: string) {
    setBusy(key)
    try {
      const updated = await work()
      if (updated) onUpdated(updated)
      toast.success(success)
      onChanged?.()
    } catch (error) {
      toast.error(error)
    } finally {
      setBusy(null)
    }
  }

  const save = () =>
    run(
      'save',
      () =>
        api.content.update(piece.id, {
          title: draft.title,
          body: draft.body,
          hashtags,
          pillar: draft.pillar,
          target_keyword: draft.target_keyword,
        }),
      'Changes saved',
    )

  const act = (action: Action) => {
    if (action === 'request_changes' && !note.trim()) {
      toast.error('Add a note so the team knows what to change')
      return
    }
    const extra =
      action === 'request_changes'
        ? { note }
        : action === 'schedule'
          ? { scheduled_at: new Date(slot).toISOString() }
          : undefined
    return run(action, async () => {
      if (dirty && team) await api.content.update(piece.id, { title: draft.title, body: draft.body, hashtags })
      const updated = await api.content.transition(piece.id, action, extra)
      if (action === 'request_changes') setNote('')
      return updated
    }, `${ACTION_LABELS[action]}: done`)
  }

  const postComment = () =>
    run(
      'comment',
      async () => {
        const updated = await api.content.transition(piece.id, 'comment', { note: comment })
        setComment('')
        return updated
      },
      'Comment added',
    )

  const syncMetrics = () =>
    run(
      'sync',
      async () => {
        const result = await api.content.syncMetrics(piece.id)
        toast.info(result.note)
        return result.item
      },
      'Metrics synced',
    )

  const repurpose = () =>
    run(
      'repurpose',
      async () => {
        const result = await api.ai.repurpose(piece.id, repurposeTo)
        toast.info(`New ${CHANNEL_LABELS[repurposeTo]} draft created (${result.source === 'template' ? 'template' : 'AI'})`)
      },
      'Repurposed into a new draft',
    )

  const remove = () => {
    if (!window.confirm('Delete this piece? This cannot be undone.')) return
    void run('delete', () => api.content.remove(piece.id), 'Deleted').then(onClose)
  }

  return (
    <Drawer
      title={piece.title || 'Untitled'}
      onClose={onClose}
      subtitle={
        <div className="row wrap">
          <StatusBadge status={piece.status as ContentStatus} />
          <span className="chip">{CHANNEL_LABELS[piece.channel]}</span>
          <span className="chip">{humanize(piece.format)}</span>
          {piece.ai_generated ? <SourceBadge source={piece.ai_source || 'template'} /> : null}
          <span className="subtle">
            {piece.client.name} · {piece.client.company}
          </span>
        </div>
      }
      footer={
        actions.length || (team && dirty) ? (
          <div className="stack grow">
            {actions.includes('request_changes') ? (
              <Field label="Note for the team (required to request changes)">
                <textarea
                  className="textarea"
                  style={{ minHeight: 60 }}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="What should change?"
                />
              </Field>
            ) : null}
            {actions.includes('schedule') ? (
              <Field label="Publish slot">
                <input className="input" type="datetime-local" value={slot} onChange={(e) => setSlot(e.target.value)} />
              </Field>
            ) : null}
            <div className="row wrap">
              {team && dirty ? (
                <Button variant="primary" busy={busy === 'save'} onClick={save}>
                  Save changes
                </Button>
              ) : null}
              {actions.map((action) => (
                <Button
                  key={action}
                  variant={PRIMARY.includes(action) ? 'primary' : action === 'request_changes' ? 'danger' : 'default'}
                  busy={busy === action}
                  disabled={busy !== null && busy !== action}
                  onClick={() => void act(action)}
                >
                  {ACTION_LABELS[action]}
                </Button>
              ))}
            </div>
          </div>
        ) : null
      }
    >
      <div className="stack">
        {piece.scheduled_at && piece.status === 'scheduled' ? (
          <div className="callout">Scheduled for {dateTime(piece.scheduled_at)}</div>
        ) : null}

        {editable ? (
          <div className="form-grid">
            <Field label="Title" full>
              <input className="input" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
            </Field>
            <Field label="Copy" full>
              <textarea
                className="textarea"
                style={{ minHeight: 260 }}
                value={draft.body}
                onChange={(e) => setDraft({ ...draft, body: e.target.value })}
              />
            </Field>
            <Field label="Hashtags">
              <input className="input" value={draft.hashtags} onChange={(e) => setDraft({ ...draft, hashtags: e.target.value })} />
            </Field>
            <Field label="Pillar">
              <input className="input" value={draft.pillar} onChange={(e) => setDraft({ ...draft, pillar: e.target.value })} />
            </Field>
            <Field label="Target keyword" full>
              <input
                className="input"
                value={draft.target_keyword}
                onChange={(e) => setDraft({ ...draft, target_keyword: e.target.value })}
              />
            </Field>
          </div>
        ) : (
          <PostPreview channel={piece.channel} body={piece.body} hashtags={piece.hashtags} author={piece.client} />
        )}

        {piece.status === 'published' ? (
          <div className="card card-body stack tight">
            <div className="row between">
              <h3>Performance</h3>
              <SimulatedBadge />
            </div>
            <div className="row wrap" style={{ gap: 24 }}>
              <span>
                <strong>{num(piece.metrics.impressions)}</strong> <span className="muted">impressions</span>
              </span>
              <span>
                <strong>{num(piece.metrics.engagements)}</strong> <span className="muted">engagements</span>
              </span>
              <span>
                <strong>{num(piece.metrics.clicks)}</strong> <span className="muted">clicks</span>
              </span>
              <span>
                <strong>{num(piece.metrics.leads)}</strong> <span className="muted">leads</span>
              </span>
            </div>
            <span className="subtle">Published {dateTime(piece.published_at)}</span>
            {team ? (
              <div>
                <Button size="sm" busy={busy === 'sync'} onClick={syncMetrics}>
                  Sync metrics
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}

        {team ? (
          <div className="row wrap">
            <span className="muted">Repurpose into</span>
            <select className="select" style={{ width: 160 }} value={repurposeTo} onChange={(e) => setRepurposeTo(e.target.value as Channel)}>
              {CHANNELS.filter((c) => c !== piece.channel).map((c) => (
                <option key={c} value={c}>
                  {CHANNEL_LABELS[c]}
                </option>
              ))}
            </select>
            <Button size="sm" busy={busy === 'repurpose'} onClick={repurpose}>
              Repurpose
            </Button>
            <span className="grow" />
            <Button size="sm" variant="ghost" onClick={remove}>
              Delete
            </Button>
          </div>
        ) : null}

        <div>
          <div className="section-title">Approval timeline</div>
          <ol className="timeline">
            {piece.events.map((event) => (
              <li key={event.id}>
                <div className="row wrap">
                  <strong>{event.user?.name ?? 'System'}</strong>
                  <span className="muted">{EVENT_LABELS[event.action] ?? humanize(event.action)}</span>
                  {event.from_status && event.to_status && event.from_status !== event.to_status ? (
                    <span className="subtle">
                      {STATUS_META[event.from_status as ContentStatus]?.label ?? event.from_status} →{' '}
                      {STATUS_META[event.to_status as ContentStatus]?.label ?? event.to_status}
                    </span>
                  ) : null}
                  {event.user?.role === 'client' ? <Badge tone="amber" plain>Client</Badge> : null}
                  <span className="subtle" title={dateTime(event.created_at)}>
                    {relative(event.created_at)}
                  </span>
                </div>
                {event.note ? <div className="note">{event.note}</div> : null}
              </li>
            ))}
          </ol>
        </div>

        {piece.allowed_actions.includes('comment') ? (
          <div className="stack tight">
            <Field label="Add a comment">
              <textarea
                className="textarea"
                style={{ minHeight: 60 }}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={team ? 'Note for the team or client' : 'Ask a question or leave feedback'}
              />
            </Field>
            <div>
              <Button size="sm" disabled={!comment.trim()} busy={busy === 'comment'} onClick={postComment}>
                Comment
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </Drawer>
  )
}
