export type DealStage =
  | 'discovery'
  | 'qualification'
  | 'proposal'
  | 'negotiation'
  | 'closed_won'
  | 'closed_lost'

export type ActivityType = 'note' | 'email' | 'call' | 'meeting' | 'stage_change' | 'system'

export interface PipelineStageSummary {
  stage: DealStage
  count: number
  amount_minor: number
  weighted_amount_minor: number
}

export interface ActivitySummary {
  id: string
  activity_type: ActivityType
  body: string
  actor: string
  occurred_at: string
  company_id?: string | null
  lead_id?: string | null
  deal_id?: string | null
  metadata: Record<string, unknown>
}

export interface AuditEventSummary {
  id: string
  event_type: string
  actor: string
  entity_type: string
  entity_id: string
  occurred_at: string
  payload: Record<string, unknown>
}

export interface DashboardOverview {
  generated_at: string
  pipeline_totals: {
    currency: string
    total_count: number
    total_amount_minor: number
    weighted_amount_minor: number
  }
  stage_summaries: PipelineStageSummary[]
  risk_counts: {
    total: number
    pending: number
    approved: number
    rejected: number
    by_type: Record<string, number>
  }
  recent_activities: ActivitySummary[]
  recent_audit_events: AuditEventSummary[]
}

export interface ApprovalEvidence {
  source_id: string
  source_type: 'call_transcript'
  summary: string
  occurred_at: string
}

export interface ApprovalRecord {
  id: string
  risk_type: 'missing_economic_buyer'
  status: 'pending' | 'approved' | 'rejected'
  deal_id: string
  company_id: string
  company_name: string
  deal_name: string
  deal_stage: string
  amount_minor: number
  created_at: string
  evidence: ApprovalEvidence[]
  decided_at?: string | null
  decided_by?: string | null
  decision_note?: string | null
}

export interface LeadSummary {
  id: string
  company_id: string
  company_name: string
  name: string
  title: string
  email: string
  status: string
  score: number
  owner: string
}

export interface DealDetail {
  id: string
  company_id: string
  primary_lead_id: string | null
  name: string
  stage: DealStage
  amount_minor: number
  currency: string
  close_date: string
  probability: number
  owner: string
  version: number
}

export interface StageChange {
  id: string
  deal_id: string
  from_stage: DealStage | null
  to_stage: DealStage
  reason: string
  actor: string
  occurred_at: string
}

export interface DealResponse {
  deal: DealDetail
  company: {
    id: string
    name: string
    domain: string
    industry: string
    employee_band: string
    region: string
  }
  primary_lead: LeadSummary | null
  recent_activities: ActivitySummary[]
  stage_history: StageChange[]
}

export interface SearchLeadsResponse {
  items: LeadSummary[]
  next_cursor: string | null
  total_estimate: number
}

export interface AgentAskResponse {
  request: string
  actor: string
  trace_id: string
  intent: string | null
  tool_name: string | null
  response: string
  observations: Array<Record<string, unknown>>
  errors: string[]
}

export interface UpdateStageResponse {
  deal: DealDetail
  stage_change: StageChange
}

export type SignalEventType =
  | 'funding_round'
  | 'executive_change'
  | 'layoffs'
  | 'tech_stack_change'
  | 'competitor_mention'
  | 'expansion'

export type SignalStatus = 'new' | 'acknowledged' | 'dismissed'

export interface SignalEventRecord {
  id: string
  company_id: string
  company_name: string
  company_domain: string
  event_type: SignalEventType
  headline: string
  summary: string
  source: string
  source_url?: string | null
  occurred_at: string
  status: SignalStatus
  relevance_score: number
  suggested_action: string
  payload: Record<string, unknown>
}
