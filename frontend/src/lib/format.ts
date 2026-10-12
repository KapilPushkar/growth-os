// Labels, status tones and formatters shared by every screen, so a status
// looks the same wherever it appears.
import type {
  Action,
  CampaignType,
  Channel,
  ContentStatus,
  Engine,
  LeadSource,
  LeadStage,
} from './types'

export type Tone = 'neutral' | 'slate' | 'violet' | 'amber' | 'red' | 'teal' | 'blue' | 'green' | 'orange'

export const CONTENT_STATUSES: ContentStatus[] = [
  'idea',
  'draft',
  'internal_review',
  'client_review',
  'changes_requested',
  'approved',
  'scheduled',
  'published',
]

export const STATUS_META: Record<ContentStatus, { label: string; tone: Tone }> = {
  idea: { label: 'Idea', tone: 'neutral' },
  draft: { label: 'Draft', tone: 'slate' },
  internal_review: { label: 'Internal review', tone: 'violet' },
  client_review: { label: 'With client', tone: 'amber' },
  changes_requested: { label: 'Changes requested', tone: 'red' },
  approved: { label: 'Approved', tone: 'teal' },
  scheduled: { label: 'Scheduled', tone: 'blue' },
  published: { label: 'Published', tone: 'green' },
}

export const LEAD_STAGES: LeadStage[] = ['new', 'contacted', 'engaged', 'meeting_booked', 'proposal', 'won', 'lost']

export const STAGE_META: Record<LeadStage, { label: string; tone: Tone }> = {
  new: { label: 'New', tone: 'neutral' },
  contacted: { label: 'Contacted', tone: 'blue' },
  engaged: { label: 'Engaged', tone: 'violet' },
  meeting_booked: { label: 'Meeting booked', tone: 'amber' },
  proposal: { label: 'Proposal', tone: 'orange' },
  won: { label: 'Won', tone: 'green' },
  lost: { label: 'Lost', tone: 'red' },
}

export const CLIENT_STATUS_TONE: Record<string, Tone> = {
  onboarding: 'amber',
  active: 'green',
  paused: 'neutral',
}

export const CHANNELS: Channel[] = ['linkedin', 'x', 'blog', 'newsletter', 'instagram']
export const CHANNEL_LABELS: Record<Channel, string> = {
  linkedin: 'LinkedIn',
  x: 'X',
  blog: 'Blog',
  newsletter: 'Newsletter',
  instagram: 'Instagram',
}
export const DEFAULT_FORMAT = {
  linkedin: 'post',
  x: 'thread',
  blog: 'article',
  newsletter: 'article',
  instagram: 'carousel',
} as const

export const CAMPAIGN_TYPE_LABELS: Record<CampaignType, string> = {
  content: 'Content',
  personal_brand: 'Personal brand',
  lead_gen: 'Lead generation',
  performance: 'Performance',
}

export const SOURCE_LABELS: Record<LeadSource, string> = {
  content: 'From content',
  inbound: 'Inbound',
  outbound: 'Outbound',
  referral: 'Referral',
}

export const ENGINES: Engine[] = ['chatgpt', 'perplexity', 'gemini', 'claude']
export const ENGINE_LABELS: Record<Engine, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
  claude: 'Claude',
}

export const ACTION_LABELS: Record<Action, string> = {
  submit: 'Submit for review',
  send_to_client: 'Send to client',
  reject_internal: 'Return to draft',
  approve: 'Approve',
  request_changes: 'Request changes',
  revise: 'Move to draft',
  schedule: 'Schedule',
  publish: 'Mark published',
  comment: 'Comment',
}

export const EVENT_LABELS: Record<string, string> = {
  ...ACTION_LABELS,
  create: 'Created',
  auto_approve: 'Auto-approved',
  approve: 'Approved',
  request_changes: 'Requested changes',
  comment: 'Commented',
  schedule: 'Scheduled',
  publish: 'Published',
  submit: 'Submitted for review',
  send_to_client: 'Sent to client',
}

export const KPI_LABELS: Record<string, string> = {
  posts: 'Posts published',
  impressions: 'Impressions',
  engagements: 'Engagements',
  leads: 'Leads',
  meetings: 'Meetings',
}

export function humanize(value: string): string {
  const text = value.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 })
const whole = new Intl.NumberFormat('en')

export function num(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return Math.abs(value) >= 10000 ? compact.format(value) : whole.format(Math.round(value * 10) / 10)
}

export function money(value: number | null | undefined): string {
  if (!value) return '—'
  return `$${compact.format(value)}`
}

export function pct(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return '—'
  return `${value.toFixed(digits)}%`
}

export function signedPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'no prior data'
  const rounded = Math.round(value)
  return `${rounded > 0 ? '+' : ''}${rounded}%`
}

export function date(value: string | null | undefined, options?: Intl.DateTimeFormatOptions): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString(undefined, options ?? { day: 'numeric', month: 'short', year: 'numeric' })
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function relative(value: string | null | undefined): string {
  if (!value) return '—'
  const diff = Date.now() - new Date(value).getTime()
  const minutes = Math.round(diff / 60000)
  if (Math.abs(minutes) < 1) return 'just now'
  const future = minutes < 0
  const abs = Math.abs(minutes)
  const unit = abs < 60 ? `${abs}m` : abs < 60 * 48 ? `${Math.round(abs / 60)}h` : `${Math.round(abs / 1440)}d`
  return future ? `in ${unit}` : `${unit} ago`
}

export function waited(hours: number): string {
  if (hours < 1) return '<1h'
  if (hours < 48) return `${Math.round(hours)}h`
  return `${Math.round(hours / 24)}d`
}

export function initials(name: string): string {
  return name
    .replace(/^Dr\.?\s+/i, '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

/** Value for <input type="datetime-local"> in the viewer's timezone. */
export function toLocalInput(value: Date): string {
  const offset = value.getTimezoneOffset() * 60000
  return new Date(value.getTime() - offset).toISOString().slice(0, 16)
}

export function sourceLabel(source: string | null | undefined): string {
  if (!source) return ''
  if (source.startsWith('llm:')) return `AI · ${humanize(source.slice(4))}`
  return 'Template'
}

export function healthTone(score: number | null): Tone {
  if (score === null) return 'neutral'
  if (score >= 75) return 'green'
  if (score >= 50) return 'amber'
  return 'red'
}
