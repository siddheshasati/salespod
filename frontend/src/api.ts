import type {
  AgentAskResponse,
  ApprovalRecord,
  AuditEventSummary,
  DashboardOverview,
  DealResponse,
  DealStage,
  SearchLeadsResponse,
  SignalEventRecord,
  UpdateStageResponse,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { message?: string } | null
    throw new Error(error?.message ?? `Request failed (${response.status})`)
  }

  return response.json() as Promise<T>
}

export const api = {
  getOverview: () => request<DashboardOverview>('/api/dashboard/overview'),
  getApprovals: () => request<ApprovalRecord[]>('/api/approvals'),
  getAuditEvents: () => request<AuditEventSummary[]>('/api/audit/events?limit=100'),
  getSignals: (status?: string) =>
    request<SignalEventRecord[]>(`/api/signals?limit=50${status ? `&status=${encodeURIComponent(status)}` : ''}`),
  acknowledgeSignal: (signalId: string, note?: string) =>
    request<SignalEventRecord>(`/api/signals/${signalId}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ actor: 'manager', note: note || undefined }),
    }),
  getDeal: (dealId: string) => request<DealResponse>(`/api/deals/${dealId}`),
  searchLeads: (query: string) =>
    request<SearchLeadsResponse>(`/api/leads?query=${encodeURIComponent(query)}&limit=8`),
  askAgent: (requestText: string, actor = 'manager') =>
    request<AgentAskResponse>('/api/agent/ask', {
      method: 'POST',
      body: JSON.stringify({ request: requestText, actor }),
    }),
  decideApproval: (approvalId: string, decision: 'approved' | 'rejected', note: string) =>
    request<ApprovalRecord>(`/api/approvals/${approvalId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, actor: 'manager', note: note || undefined }),
    }),
  updateStage: (
    dealId: string,
    payload: { new_stage: DealStage; reason: string; expected_version: number },
  ) =>
    request<UpdateStageResponse>(`/api/deals/${dealId}/stage`, {
      method: 'POST',
      body: JSON.stringify({ ...payload, actor: 'manager' }),
    }),
}
