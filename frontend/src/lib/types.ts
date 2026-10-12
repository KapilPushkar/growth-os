// API contract, mirroring backend/app/serializers.py.

export type Role = 'admin' | 'strategist' | 'client'
export type ClientStatus = 'onboarding' | 'active' | 'paused'
export type Channel = 'linkedin' | 'x' | 'blog' | 'newsletter' | 'instagram'
export type ContentFormat = 'post' | 'carousel' | 'article' | 'thread' | 'video_script'
export type ContentStatus =
  | 'idea'
  | 'draft'
  | 'internal_review'
  | 'client_review'
  | 'changes_requested'
  | 'approved'
  | 'scheduled'
  | 'published'
export type Action =
  | 'submit'
  | 'send_to_client'
  | 'reject_internal'
  | 'approve'
  | 'request_changes'
  | 'revise'
  | 'schedule'
  | 'publish'
  | 'comment'
export type CampaignType = 'content' | 'personal_brand' | 'lead_gen' | 'performance'
export type CampaignStatus = 'planned' | 'active' | 'paused' | 'completed'
export type LeadStage =
  | 'new'
  | 'contacted'
  | 'engaged'
  | 'meeting_booked'
  | 'proposal'
  | 'won'
  | 'lost'
export type LeadSource = 'content' | 'inbound' | 'outbound' | 'referral'
export type OutreachKind = 'connection_note' | 'follow_up' | 'meeting_request'
export type Engine = 'chatgpt' | 'perplexity' | 'gemini' | 'claude'
export type AiSource = 'llm:anthropic' | 'llm:openai' | 'template' | string

export interface User {
  id: number
  email: string
  name: string
  role: Role
  client_id: number | null
  is_active: boolean
}

export interface ClientBrief {
  id: number
  name: string
  title: string
  company: string
}

export interface Me extends User {
  client: ClientBrief | null
}

export interface OnboardingStep {
  key: string
  label: string
  done: boolean
}

export interface Client {
  id: number
  name: string
  title: string
  email: string
  company: string
  industry: string
  website: string
  plan: string
  status: ClientStatus
  positioning: string
  brand_voice: string
  tone_tags: string[]
  target_audience: string
  content_pillars: string[]
  topics_to_avoid: string
  goals: string[]
  channels: Channel[]
  posting_cadence: number
  auto_approve_hours: number
  onboarding: OnboardingStep[]
  onboarding_pct: number
  account_manager_id: number | null
  account_manager: { id: number; name: string | null } | null
  start_date: string | null
  created_at: string
  health: number | null
  approvals_waiting: number
}

export interface ApprovalEvent {
  id: number
  action: string
  from_status: string | null
  to_status: string | null
  note: string
  created_at: string
  user: { id: number; name: string; role: Role } | null
}

export interface Metrics {
  impressions: number
  engagements: number
  clicks: number
  leads: number
}

export interface Content {
  id: number
  client_id: number
  campaign_id: number | null
  title: string
  channel: Channel
  format: ContentFormat
  pillar: string
  body: string
  hashtags: string[]
  target_keyword: string
  status: ContentStatus
  status_changed_at: string
  scheduled_at: string | null
  published_at: string | null
  ai_generated: boolean
  ai_source: string
  metrics: Metrics
  created_at: string
  updated_at: string
  client_name?: string | null
}

export interface ContentDetail extends Content {
  events: ApprovalEvent[]
  allowed_actions: Action[]
  client: ClientBrief
}

export interface QueueItem extends Content {
  allowed_actions: Action[]
  client: ClientBrief
  waiting_hours: number
  auto_approve_in_hours: number | null
}

export interface Approvals {
  internal_review: QueueItem[]
  client_review: QueueItem[]
  changes_requested: QueueItem[]
}

export interface BulkResult {
  done: Content[]
  errors: { id: number; status_code: number; detail: string }[]
}

export interface KpiProgress {
  target: number
  actual: number
  pct: number
}

export interface Campaign {
  id: number
  client_id: number
  name: string
  type: CampaignType
  status: CampaignStatus
  objective: string
  channels: Channel[]
  start_date: string | null
  end_date: string | null
  kpi_targets: Record<string, number>
  progress: Record<string, KpiProgress>
  created_at: string
}

export interface Lead {
  id: number
  client_id: number
  campaign_id: number | null
  content_id: number | null
  name: string
  title: string
  company: string
  email: string
  linkedin_url: string
  source: LeadSource
  stage: LeadStage
  score: number
  deal_value: number
  notes: string
  stage_changed_at: string
  created_at: string
  updated_at: string
  client_name?: string | null
}

export interface LeadSummary {
  total: number
  by_stage: { stage: LeadStage; count: number; value: number }[]
  open_value: number
  won_value: number
}

export interface Pipeline {
  stages: { stage: LeadStage; leads: Lead[]; value: number }[]
  summary: LeadSummary
}

export interface Keyword {
  id: number
  client_id: number
  keyword: string
  intent: string
  search_volume: number
  difficulty: number
  current_rank: number | null
  previous_rank: number | null
  rank_change: number | null
  trend: string
  target_url: string
  updated_at: string
}

export interface GeoCheck {
  id: number
  client_id: number
  prompt: string
  engine: Engine
  mentioned: boolean
  position: number | null
  method: 'live' | 'simulated'
  excerpt: string
  checked_at: string
}

export interface GeoEngineSummary {
  engine: Engine
  checks: number
  mentioned: number
  visibility_pct: number
  method: 'live' | 'simulated'
}

export interface GeoOverview {
  checks: GeoCheck[]
  by_engine: GeoEngineSummary[]
  prompts: string[]
}

export interface Snapshot {
  week_start: string
  followers: number
  impressions: number
  engagements: number
  profile_views: number
  website_visits: number
  leads: number
  meetings: number
  ai_visibility: number
}

export interface Kpi {
  key: string
  label: string
  current: number
  previous: number
  change_pct: number | null
}

export interface Impact {
  client_id: number
  weeks: number
  kpis: Kpi[]
  series: Snapshot[]
  funnel: { stage: string; label: string; value: number }[]
  top_posts: Content[]
  keyword_movers: Keyword[]
  geo: GeoEngineSummary[]
  leads: LeadSummary
  health: number | null
}

export interface Report {
  client: ClientBrief & { industry: string; goals: string[] }
  period: { start: string; end: string; days: number }
  kpis: Kpi[]
  highlights: {
    posts_published: number
    new_leads: number
    meetings_booked: number
    deals_won: number
    won_value: number
  }
  series: Snapshot[]
  top_content: Content[]
  leads_won: Lead[]
  keyword_movers: Keyword[]
  geo: GeoEngineSummary[]
  summary: string
  next_steps: string[]
  summary_source: AiSource
}

export interface DashboardClientRow {
  id: number
  name: string
  company: string
  industry: string
  status: ClientStatus
  account_manager_id: number | null
  health: number | null
  onboarding_pct: number
  approvals_waiting: number
  internal_review: number
  changes_requested: number
  scheduled: number
  impressions_series: number[]
  impressions_change_pct: number | null
}

export interface Activity {
  id: number
  client_id: number | null
  client_name: string | null
  kind: string
  message: string
  user: string
  created_at: string
}

export interface Dashboard {
  totals: {
    active_clients: number
    onboarding_clients: number
    published_this_week: number
    awaiting_approval: number
    internal_review: number
    changes_requested: number
    leads_this_month: number
    pipeline_value: number
  }
  clients: DashboardClientRow[]
  onboarding_pipeline: {
    step: string
    label: string
    clients: { id: number; name: string; company: string; onboarding_pct: number }[]
  }[]
  activity: Activity[]
  generated_at: string
}

export interface Topic {
  topic: string
  angle: string
  pillar: string
  why_now: string
  channel: Channel
  keywords: string[]
  momentum: 'breakout' | 'rising' | 'steady'
  momentum_score: number
}

export interface KeywordIdea {
  keyword: string
  intent: string
  search_volume: number
  difficulty: number
  rationale: string
}

export interface AiStatus {
  provider: 'anthropic' | 'openai' | 'none'
  model: string | null
  mode: 'llm' | 'template'
}

export interface Outreach {
  kind: OutreachKind
  subject: string
  message: string
  lead_id: number
  source: AiSource
}
