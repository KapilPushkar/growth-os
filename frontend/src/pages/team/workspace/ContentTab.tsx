import { useState } from 'react'
import { ContentEditor } from '../../../components/ContentEditor'
import {
  Badge,
  Button,
  Card,
  Empty,
  ErrorState,
  Field,
  Loading,
  Modal,
  SourceBadge,
  StatusBadge,
} from '../../../components/ui'
import { api } from '../../../lib/api'
import { CHANNEL_LABELS, CONTENT_STATUSES, DEFAULT_FORMAT, dateTime, humanize, relative } from '../../../lib/format'
import { useToast } from '../../../lib/toast'
import type { Channel, Client, ContentFormat, Topic } from '../../../lib/types'
import { useApi } from '../../../lib/useApi'

const FORMATS: ContentFormat[] = ['post', 'carousel', 'article', 'thread', 'video_script']
const MOMENTUM_TONE = { breakout: 'red', rising: 'amber', steady: 'neutral' } as const

export function ContentTab({ client }: { client: Client }) {
  const [channel, setChannel] = useState<Channel | ''>('')
  const [openId, setOpenId] = useState<number | null>(null)
  const [creating, setCreating] = useState(false)
  const board = useApi(() => api.content.list({ client_id: client.id, channel: channel || undefined }), [client.id, channel])

  return (
    <div className="stack">
      <AiStudio client={client} onGenerated={board.reload} onOpen={setOpenId} />

      <Card
        title="Content board"
        subtitle={board.data ? `${board.data.length} pieces` : undefined}
        actions={
          <>
            <select
              className="select"
              style={{ width: 160 }}
              value={channel}
              onChange={(e) => setChannel(e.target.value as Channel | '')}
              aria-label="Channel"
            >
              <option value="">All channels</option>
              {client.channels.map((c) => (
                <option key={c} value={c}>
                  {CHANNEL_LABELS[c]}
                </option>
              ))}
            </select>
            <Button onClick={() => setCreating(true)}>New draft</Button>
          </>
        }
        bodyless
      >
        {board.error ? (
          <ErrorState message={board.error} onRetry={board.reload} />
        ) : !board.data ? (
          <Loading />
        ) : board.data.length === 0 ? (
          <Empty title="No content yet">Generate drafts with the AI Studio above, or write one from scratch.</Empty>
        ) : (
          <div className="board" style={{ padding: 16 }}>
            {CONTENT_STATUSES.map((status) => {
              const items = board.data!.filter((piece) => piece.status === status)
              return (
                <div className="board-col" key={status}>
                  <div className="board-col-header">
                    <StatusBadge status={status} />
                    <span className="subtle">{items.length}</span>
                  </div>
                  {items.map((piece) => (
                    <button type="button" key={piece.id} className="board-card" onClick={() => setOpenId(piece.id)}>
                      <span className="title">{piece.title || 'Untitled'}</span>
                      <div className="row wrap">
                        <span className="chip">{CHANNEL_LABELS[piece.channel]}</span>
                        {piece.pillar ? <span className="chip">{piece.pillar}</span> : null}
                        {piece.ai_generated ? <SourceBadge source={piece.ai_source || 'template'} /> : null}
                      </div>
                      <span className="subtle">
                        {piece.status === 'scheduled'
                          ? `Goes out ${dateTime(piece.scheduled_at)}`
                          : piece.status === 'published'
                            ? `Published ${relative(piece.published_at)}`
                            : `Updated ${relative(piece.status_changed_at)}`}
                      </span>
                    </button>
                  ))}
                </div>
              )
            })}
          </div>
        )}
      </Card>

      {openId !== null ? <ContentEditor contentId={openId} onClose={() => setOpenId(null)} onChanged={board.reload} /> : null}
      {creating ? (
        <NewDraftModal
          client={client}
          onClose={() => setCreating(false)}
          onCreated={(id) => {
            setCreating(false)
            board.reload()
            setOpenId(id)
          }}
        />
      ) : null}
    </div>
  )
}

function AiStudio({
  client,
  onGenerated,
  onOpen,
}: {
  client: Client
  onGenerated: () => void
  onOpen: (id: number) => void
}) {
  const toast = useToast()
  const topics = useApi(() => api.ai.topics(client.id, 6), [client.id])
  const campaigns = useApi(() => api.campaigns.list(client.id), [client.id])
  const [generating, setGenerating] = useState(false)
  const [last, setLast] = useState<{ count: number; source: string; firstId: number } | null>(null)
  const [form, setForm] = useState({
    pillar: client.content_pillars[0] ?? '',
    channel: (client.channels[0] ?? 'linkedin') as Channel,
    format: DEFAULT_FORMAT[client.channels[0] ?? 'linkedin'] as ContentFormat,
    topic: '',
    keyword: '',
    count: 3,
    campaign_id: 0,
  })

  function applyTopic(topic: Topic) {
    const channel = client.channels.includes(topic.channel) ? topic.channel : form.channel
    setForm({
      ...form,
      topic: topic.topic,
      pillar: client.content_pillars.includes(topic.pillar) ? topic.pillar : form.pillar,
      channel,
      format: DEFAULT_FORMAT[channel],
      keyword: topic.keywords[0] ?? '',
    })
    toast.info('Topic added to the generator')
  }

  async function generate() {
    setGenerating(true)
    try {
      const result = await api.ai.generate({
        client_id: client.id,
        channel: form.channel,
        format: form.format,
        pillar: form.pillar,
        topic: form.topic,
        keyword: form.keyword,
        count: form.count,
        campaign_id: form.campaign_id || null,
      })
      setLast({ count: result.items.length, source: result.source, firstId: result.items[0]?.id })
      toast.success(`${result.items.length} draft${result.items.length === 1 ? '' : 's'} added to the board`)
      onGenerated()
    } catch (error) {
      toast.error(error)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <Card
      title="AI Studio"
      subtitle={`Drafts are written from ${client.name}'s brand profile and always start as drafts for review.`}
      bodyless
    >
      <div className="grid main-side" style={{ padding: 20 }}>
        <div className="stack tight">
          <div className="row between">
            <div className="section-title" style={{ margin: 0 }}>
              Trending topics
            </div>
            <div className="row">
              {topics.data ? <SourceBadge source={topics.data.source} /> : null}
              <Button size="sm" variant="ghost" busy={topics.loading} onClick={topics.reload}>
                Refresh
              </Button>
            </div>
          </div>
          {topics.error && !topics.data ? (
            <ErrorState message={topics.error} onRetry={topics.reload} />
          ) : !topics.data ? (
            <Loading compact label="Finding timely topics…" />
          ) : (
            <ul className="list card">
              {topics.data.topics.map((topic) => (
                <li key={topic.topic}>
                  <div className="grow stack tight" style={{ gap: 4 }}>
                    <div className="row wrap">
                      <strong>{topic.topic}</strong>
                      <Badge tone={MOMENTUM_TONE[topic.momentum]} plain>
                        {humanize(topic.momentum)} · {topic.momentum_score}
                      </Badge>
                    </div>
                    <span className="muted">{topic.angle}</span>
                    <span className="subtle">
                      Why now: {topic.why_now} · {topic.pillar} · {CHANNEL_LABELS[topic.channel] ?? topic.channel}
                    </span>
                  </div>
                  <Button size="sm" onClick={() => applyTopic(topic)}>
                    Use this topic
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="stack tight">
          <div className="section-title" style={{ margin: 0 }}>
            Generate drafts
          </div>
          <div className="form-grid">
            <Field label="Pillar">
              <select className="select" value={form.pillar} onChange={(e) => setForm({ ...form, pillar: e.target.value })}>
                {client.content_pillars.map((pillar) => (
                  <option key={pillar}>{pillar}</option>
                ))}
              </select>
            </Field>
            <Field label="Channel">
              <select
                className="select"
                value={form.channel}
                onChange={(e) => {
                  const channel = e.target.value as Channel
                  setForm({ ...form, channel, format: DEFAULT_FORMAT[channel] })
                }}
              >
                {client.channels.map((c) => (
                  <option key={c} value={c}>
                    {CHANNEL_LABELS[c]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Format">
              <select className="select" value={form.format} onChange={(e) => setForm({ ...form, format: e.target.value as ContentFormat })}>
                {FORMATS.map((f) => (
                  <option key={f} value={f}>
                    {humanize(f)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="How many">
              <input
                className="input"
                type="number"
                min={1}
                max={5}
                value={form.count}
                onChange={(e) => setForm({ ...form, count: Math.max(1, Math.min(5, Number(e.target.value))) })}
              />
            </Field>
            <Field label="Topic" full>
              <input
                className="input"
                value={form.topic}
                onChange={(e) => setForm({ ...form, topic: e.target.value })}
                placeholder="Defaults to the pillar"
              />
            </Field>
            <Field label="Target keyword">
              <input className="input" value={form.keyword} onChange={(e) => setForm({ ...form, keyword: e.target.value })} />
            </Field>
            <Field label="Campaign">
              <select
                className="select"
                value={form.campaign_id}
                onChange={(e) => setForm({ ...form, campaign_id: Number(e.target.value) })}
              >
                <option value={0}>None</option>
                {(campaigns.data ?? []).map((campaign) => (
                  <option key={campaign.id} value={campaign.id}>
                    {campaign.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="row wrap">
            <Button variant="primary" busy={generating} onClick={generate} disabled={!client.content_pillars.length}>
              Generate {form.count} draft{form.count === 1 ? '' : 's'}
            </Button>
            {last ? (
              <>
                <SourceBadge source={last.source} />
                <Button size="sm" variant="ghost" onClick={() => onOpen(last.firstId)}>
                  Open first draft
                </Button>
              </>
            ) : null}
          </div>
          {!client.content_pillars.length ? <span className="subtle">Add content pillars in the brand profile first.</span> : null}
        </div>
      </div>
    </Card>
  )
}

function NewDraftModal({
  client,
  onClose,
  onCreated,
}: {
  client: Client
  onClose: () => void
  onCreated: (id: number) => void
}) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    title: '',
    channel: (client.channels[0] ?? 'linkedin') as Channel,
    pillar: client.content_pillars[0] ?? '',
    body: '',
    status: 'draft' as 'draft' | 'idea',
  })

  async function submit() {
    setSaving(true)
    try {
      const piece = await api.content.create({
        client_id: client.id,
        ...form,
        format: DEFAULT_FORMAT[form.channel],
      })
      toast.success('Draft created')
      onCreated(piece.id)
    } catch (error) {
      toast.error(error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title="New piece"
      onClose={onClose}
      footer={
        <Button variant="primary" busy={saving} disabled={!form.title.trim()} onClick={submit}>
          Create
        </Button>
      }
    >
      <div className="form-grid">
        <Field label="Title" full>
          <input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} autoFocus />
        </Field>
        <Field label="Channel">
          <select className="select" value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value as Channel })}>
            {client.channels.map((c) => (
              <option key={c} value={c}>
                {CHANNEL_LABELS[c]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Start as">
          <select className="select" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as 'draft' | 'idea' })}>
            <option value="draft">Draft</option>
            <option value="idea">Idea</option>
          </select>
        </Field>
        <Field label="Pillar" full>
          <select className="select" value={form.pillar} onChange={(e) => setForm({ ...form, pillar: e.target.value })}>
            {client.content_pillars.map((pillar) => (
              <option key={pillar}>{pillar}</option>
            ))}
          </select>
        </Field>
        <Field label="Copy" full>
          <textarea className="textarea" style={{ minHeight: 180 }} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
        </Field>
      </div>
    </Modal>
  )
}
