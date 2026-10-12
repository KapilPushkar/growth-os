// Typed fetch client. Adds the stored JWT and turns non-2xx responses into
// ApiError carrying the server's `detail` message.
import type {
  Action,
  AiStatus,
  Approvals,
  BulkResult,
  Campaign,
  Channel,
  Client,
  Content,
  ContentDetail,
  ContentFormat,
  Dashboard,
  Engine,
  GeoCheck,
  GeoEngineSummary,
  GeoOverview,
  Impact,
  Keyword,
  KeywordIdea,
  Lead,
  Me,
  Metrics,
  Outreach,
  OutreachKind,
  Pipeline,
  Report,
  Topic,
  User,
} from './types'

const TOKEN_KEY = 'growth-os.token'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token: string | null) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token)
      else localStorage.removeItem(TOKEN_KEY)
    } catch {
      // Storage can be unavailable (private mode); the session then lasts one page load.
    }
  },
}

let unauthorizedHandler: (() => void) | null = null

/** Called when an authenticated request comes back 401 (expired or revoked token). */
export function onUnauthorized(handler: () => void) {
  unauthorizedHandler = handler
}

type Query = Record<string, string | number | boolean | null | undefined>

function buildQuery(query?: Query): string {
  if (!query) return ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  }
  const text = params.toString()
  return text ? `?${text}` : ''
}

function describe(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc: [...], msg: '...'}]
    return detail
      .map((item) => {
        const loc = Array.isArray(item?.loc) ? item.loc.filter((p: unknown) => p !== 'body').join('.') : ''
        const msg = String(item?.msg ?? 'Invalid value').replace(/^Value error, /, '')
        return loc ? `${loc}: ${msg}` : msg
      })
      .join('; ')
  }
  return fallback
}

async function request<T>(method: string, path: string, body?: unknown, query?: Query): Promise<T> {
  const token = tokenStore.get()
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`/api${path}${buildQuery(query)}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Is the backend running on port 8000?')
  }

  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && token) unauthorizedHandler?.()
    throw new ApiError(response.status, describe(data?.detail, response.statusText || 'Request failed'))
  }
  return data as T
}

const get = <T>(path: string, query?: Query) => request<T>('GET', path, undefined, query)
const post = <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {})
const patch = <T>(path: string, body: unknown) => request<T>('PATCH', path, body)
const del = (path: string) => request<void>('DELETE', path)

export interface ClientInput {
  name: string
  title?: string
  email?: string | null
  company: string
  industry?: string
  website?: string
  plan?: string
  positioning?: string
  brand_voice?: string
  tone_tags?: string[]
  target_audience?: string
  content_pillars?: string[]
  topics_to_avoid?: string
  goals?: string[]
  channels?: Channel[]
  posting_cadence?: number
  auto_approve_hours?: number
  account_manager_id?: number | null
  create_login?: boolean
}

export interface ContentQuery extends Query {
  client_id?: number
  status?: string
  channel?: string
  campaign_id?: number
  date_from?: string
  date_to?: string
  q?: string
}

export const api = {
  login: (email: string, password: string) =>
    post<{ access_token: string; user: Me }>('/auth/login', { email, password }),
  me: () => get<Me>('/auth/me'),
  users: (role?: string) => get<User[]>('/users', { role }),

  dashboard: () => get<Dashboard>('/dashboard'),

  clients: {
    list: (query?: { status?: string; q?: string; industry?: string }) => get<Client[]>('/clients', query),
    get: (id: number) => get<Client>(`/clients/${id}`),
    create: (input: ClientInput) =>
      post<{ client: Client; login: { email: string; temp_password: string } | null }>('/clients', input),
    update: (id: number, input: Partial<ClientInput> & { status?: string }) => patch<Client>(`/clients/${id}`, input),
    onboarding: (id: number, step: string, done: boolean) => post<Client>(`/clients/${id}/onboarding`, { step, done }),
    impact: (id: number) => get<Impact>(`/clients/${id}/impact`),
    report: (id: number, days = 30) => get<Report>(`/clients/${id}/report`, { days }),
  },

  content: {
    list: (query?: ContentQuery) => get<Content[]>('/content', query),
    get: (id: number) => get<ContentDetail>(`/content/${id}`),
    create: (input: {
      client_id: number
      channel: Channel
      format?: ContentFormat
      title?: string
      body?: string
      pillar?: string
      status?: 'idea' | 'draft'
      campaign_id?: number | null
    }) => post<ContentDetail>('/content', input),
    update: (id: number, input: Partial<Pick<Content, 'title' | 'body' | 'pillar' | 'hashtags' | 'target_keyword' | 'channel' | 'format' | 'campaign_id'>>) =>
      patch<ContentDetail>(`/content/${id}`, input),
    remove: (id: number) => del(`/content/${id}`),
    transition: (id: number, action: Action, extra?: { note?: string; scheduled_at?: string }) =>
      post<ContentDetail>(`/content/${id}/transition`, { action, ...extra }),
    bulk: (ids: number[], action: Action, note?: string) =>
      post<BulkResult>('/content/bulk-transition', { ids, action, note }),
    syncMetrics: (id: number) =>
      post<{ item: ContentDetail; delta: Metrics; method: string; note: string }>(`/content/${id}/sync-metrics`),
  },

  approvals: (clientId?: number) => get<Approvals>('/approvals', { client_id: clientId }),

  campaigns: {
    list: (clientId?: number) => get<Campaign[]>('/campaigns', { client_id: clientId }),
    create: (input: Omit<Campaign, 'id' | 'progress' | 'created_at'>) => post<Campaign>('/campaigns', input),
    update: (id: number, input: Partial<Omit<Campaign, 'id' | 'client_id' | 'progress' | 'created_at'>>) =>
      patch<Campaign>(`/campaigns/${id}`, input),
    remove: (id: number) => del(`/campaigns/${id}`),
  },

  leads: {
    list: (query?: { client_id?: number; stage?: string }) => get<Lead[]>('/leads', query),
    pipeline: (clientId?: number) => get<Pipeline>('/leads/pipeline', { client_id: clientId }),
    create: (input: Partial<Lead> & { client_id: number; name: string }) => post<Lead>('/leads', input),
    update: (id: number, input: Partial<Lead>) => patch<Lead>(`/leads/${id}`, input),
    remove: (id: number) => del(`/leads/${id}`),
  },

  keywords: {
    list: (clientId: number) => get<Keyword[]>('/keywords', { client_id: clientId }),
    bulk: (clientId: number, keywords: Omit<KeywordIdea, 'rationale'>[]) =>
      post<{ added: Keyword[]; skipped: string[] }>('/keywords/bulk', { client_id: clientId, keywords }),
    refresh: (clientId: number) =>
      post<{ items: Keyword[]; method: string; note: string }>('/keywords/refresh', { client_id: clientId }),
    remove: (id: number) => del(`/keywords/${id}`),
  },

  geo: {
    overview: (clientId: number) => get<GeoOverview>('/geo', { client_id: clientId }),
    run: (clientId: number, prompt: string, engines: Engine[]) =>
      post<{ checks: GeoCheck[]; by_engine: GeoEngineSummary[]; note: string }>('/geo/run', {
        client_id: clientId,
        prompt,
        engines,
      }),
  },

  ai: {
    status: () => get<AiStatus>('/ai/status'),
    generate: (input: {
      client_id: number
      channel: Channel
      format: ContentFormat
      pillar?: string
      topic?: string
      keyword?: string
      count: number
      campaign_id?: number | null
    }) => post<{ items: Content[]; source: string }>('/ai/generate-content', input),
    topics: (clientId: number, count = 6) =>
      post<{ topics: Topic[]; source: string }>('/ai/topics', { client_id: clientId, count }),
    keywords: (clientId: number, seed: string, count = 8) =>
      post<{ keywords: KeywordIdea[]; source: string; note: string }>('/ai/keywords', {
        client_id: clientId,
        seed,
        count,
      }),
    outreach: (leadId: number, kind: OutreachKind) => post<Outreach>('/ai/outreach', { lead_id: leadId, kind }),
    repurpose: (contentId: number, channel: Channel) =>
      post<{ item: Content; source: string }>('/ai/repurpose', { content_id: contentId, channel }),
  },
}
