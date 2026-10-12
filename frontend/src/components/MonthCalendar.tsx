import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import { isTeam, useUser } from '../lib/auth'
import { CHANNEL_LABELS, STATUS_META } from '../lib/format'
import type { Content, ContentStatus } from '../lib/types'
import { useApi } from '../lib/useApi'
import { ContentEditor } from './ContentEditor'
import { Badge, Button, Card, ErrorState, Loading } from './ui'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const SHOWN: ContentStatus[] = ['scheduled', 'published']

function startOfGrid(month: Date): Date {
  const first = new Date(month.getFullYear(), month.getMonth(), 1)
  const offset = (first.getDay() + 6) % 7 // Monday-first
  return new Date(first.getFullYear(), first.getMonth(), 1 - offset)
}

function dayKey(value: Date): string {
  return `${value.getFullYear()}-${value.getMonth()}-${value.getDate()}`
}

export function MonthCalendar({ clientId }: { clientId?: number }) {
  const user = useUser()
  const team = isTeam(user)
  const [month, setMonth] = useState(() => {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), 1)
  })
  const [filter, setFilter] = useState<number | ''>(clientId ?? '')
  const [openId, setOpenId] = useState<number | null>(null)
  const [todayKey] = useState(() => dayKey(new Date()))

  const gridStart = startOfGrid(month)
  const gridEnd = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + 42)

  const clients = useApi(() => (team && clientId === undefined ? api.clients.list({ status: 'active' }) : Promise.resolve([])), [team, clientId])
  const state = useApi(
    () =>
      api.content.list({
        client_id: filter || undefined,
        status: SHOWN.join(','),
        date_from: gridStart.toISOString(),
        date_to: gridEnd.toISOString(),
      }),
    [filter, month.getTime()],
  )

  const byDay = useMemo(() => {
    const map = new Map<string, Content[]>()
    for (const piece of state.data ?? []) {
      const when = piece.published_at ?? piece.scheduled_at
      if (!when) continue
      const key = dayKey(new Date(when))
      map.set(key, [...(map.get(key) ?? []), piece])
    }
    return map
  }, [state.data])

  const days = Array.from({ length: 42 }, (_, i) => new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i))
  const shift = (delta: number) => setMonth(new Date(month.getFullYear(), month.getMonth() + delta, 1))

  return (
    <Card
      bodyless
      title={month.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}
      subtitle={`${state.data?.length ?? 0} scheduled or published pieces`}
      actions={
        <>
          {team && clientId === undefined ? (
            <select
              className="select"
              style={{ width: 200 }}
              value={filter}
              onChange={(e) => setFilter(e.target.value ? Number(e.target.value) : '')}
              aria-label="Filter by client"
            >
              <option value="">All clients</option>
              {(clients.data ?? []).map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          ) : null}
          {SHOWN.map((status) => (
            <Badge key={status} tone={STATUS_META[status].tone}>
              {STATUS_META[status].label}
            </Badge>
          ))}
          <Button size="sm" onClick={() => shift(-1)} aria-label="Previous month">
            ←
          </Button>
          <Button size="sm" onClick={() => setMonth(new Date(new Date().getFullYear(), new Date().getMonth(), 1))}>
            Today
          </Button>
          <Button size="sm" onClick={() => shift(1)} aria-label="Next month">
            →
          </Button>
        </>
      }
    >
      {state.error ? (
        <ErrorState message={state.error} onRetry={state.reload} />
      ) : !state.data ? (
        <Loading />
      ) : (
        <div className="calendar">
          {DAYS.map((day) => (
            <div className="dow" key={day}>
              {day}
            </div>
          ))}
          {days.map((day) => {
            const key = dayKey(day)
            const items = byDay.get(key) ?? []
            const outside = day.getMonth() !== month.getMonth()
            return (
              <div className={`day${outside ? ' outside' : ''}${key === todayKey ? ' today' : ''}`} key={key}>
                <span className="date">{day.getDate()}</span>
                {items.map((piece) => (
                  <button
                    type="button"
                    key={piece.id}
                    className={`cal-item tone-${STATUS_META[piece.status].tone}`}
                    title={`${piece.client_name ?? ''} · ${CHANNEL_LABELS[piece.channel]} · ${piece.title}`}
                    onClick={() => setOpenId(piece.id)}
                  >
                    {team && !clientId && !filter ? `${piece.client_name?.replace(/^Dr\.?\s+/, '').split(' ')[0]}: ` : ''}
                    {piece.title}
                  </button>
                ))}
              </div>
            )
          })}
        </div>
      )}
      {state.data && state.data.length === 0 ? (
        <p className="subtle" style={{ padding: 16 }}>
          Nothing scheduled or published this month.
        </p>
      ) : null}
      {openId !== null ? (
        <ContentEditor contentId={openId} onClose={() => setOpenId(null)} onChanged={state.reload} />
      ) : null}
    </Card>
  )
}
