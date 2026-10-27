import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  Bot,
  Building2,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  Command,
  ExternalLink,
  FileSearch,
  Filter,
  Inbox,
  KanbanSquare,
  LayoutDashboard,
  Loader2,
  Menu,
  MessageSquareText,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  Radio,
  RefreshCw,
  Search,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Target,
  UserRound,
  Users,
  X,
  Zap,
  Mail,
  Play,
  Layers,
  SendHorizontal,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from './api'
import type {
  ActivitySummary,
  ApprovalRecord,
  AuditEventSummary,
  DashboardOverview,
  DealResponse,
  DealStage,
  LeadSummary,
  SignalEventRecord,
  SignalEventType,
  SignalPipelineResult,
} from './types'

type View = 'overview' | 'pipeline' | 'approvals' | 'signals' | 'audit'

const stageLabels: Record<DealStage, string> = {
  discovery: 'Discovery',
  qualification: 'Qualification',
  proposal: 'Proposal',
  negotiation: 'Negotiation',
  closed_won: 'Closed won',
  closed_lost: 'Closed lost',
}

const stageColors: Record<DealStage, string> = {
  discovery: '#9aa9b8',
  qualification: '#6987a0',
  proposal: '#e2a456',
  negotiation: '#f36f4f',
  closed_won: '#22a06b',
  closed_lost: '#d8dee5',
}

const navItems: Array<{ id: View; label: string; icon: typeof LayoutDashboard; badge?: string }> = [
  { id: 'overview', label: 'Command center', icon: LayoutDashboard },
  { id: 'pipeline', label: 'Pipeline', icon: KanbanSquare },
  { id: 'approvals', label: 'Approval inbox', icon: Inbox, badge: '5' },
  { id: 'signals', label: 'Signal radar', icon: Radio, badge: 'live' },
  { id: 'audit', label: 'Audit log', icon: Activity },
]

function money(minor: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(minor / 100)
}

function shortMoney(minor: number) {
  const value = minor / 100
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${Math.round(value / 1_000)}K`
  return `$${Math.round(value)}`
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(
    new Date(value),
  )
}

function relativeDate(value: string) {
  const days = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 86_400_000))
  if (days === 0) return 'Today'
  if (days === 1) return 'Yesterday'
  return `${days}d ago`
}

function todayLabel() {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date())
}

function initials(name: string) {
  return name
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

function stageLabel(stage: string) {
  return stageLabels[stage as DealStage] ?? stage.replace('_', ' ')
}

function activityIcon(type: ActivitySummary['activity_type']) {
  if (type === 'call') return <PhoneIcon />
  if (type === 'email') return <MailIcon />
  if (type === 'stage_change') return <ArrowUpRight size={14} />
  if (type === 'meeting') return <CalendarIcon />
  return <FileSearch size={14} />
}

function PhoneIcon() {
  return <span className="text-[13px]">◌</span>
}

function MailIcon() {
  return <span className="text-[13px]">@</span>
}

function CalendarIcon() {
  return <span className="text-[13px]">▦</span>
}

function StatusBadge({ status }: { status: ApprovalRecord['status'] }) {
  const styles = {
    pending: 'border-amber-200 bg-amber-50 text-amber-700',
    approved: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    rejected: 'border-rose-200 bg-rose-50 text-rose-700',
  }
  return (
    <span className={`rounded-full border px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${styles[status]}`}>
      {status}
    </span>
  )
}

function StageBadge({ stage }: { stage: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.09em] text-slate-600">
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: stageColors[stage as DealStage] ?? '#94a3b8' }} />
      {stageLabel(stage)}
    </span>
  )
}

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-ink text-white shadow-sm">
        <div className="absolute left-[9px] top-[9px] h-2 w-2 rounded-full bg-coral" />
        <div className="absolute bottom-[8px] right-[8px] h-2 w-2 rounded-full bg-amber-300" />
        <div className="h-3 w-3 rounded-full border-2 border-white/75" />
      </div>
      {!compact && (
        <div>
          <div className="text-[15px] font-extrabold tracking-[-0.04em] text-ink">salespod</div>
          <div className="text-[9px] font-bold uppercase tracking-[0.16em] text-slate-400">revenue system</div>
        </div>
      )}
    </div>
  )
}

function Sidebar({
  activeView,
  onNavigate,
  collapsed,
  onToggle,
}: {
  activeView: View
  onNavigate: (view: View) => void
  collapsed: boolean
  onToggle: () => void
}) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-slate-200/80 bg-[#fbfcfd] transition-all duration-300 lg:flex ${
        collapsed ? 'w-[82px]' : 'w-[254px]'
      }`}
    >
      <div className={`flex h-[82px] items-center border-b border-slate-200/70 ${collapsed ? 'justify-center' : 'px-6'}`}>
        <Logo compact={collapsed} />
      </div>

      <div className={`flex flex-1 flex-col py-7 ${collapsed ? 'px-3' : 'px-4'}`}>
        {!collapsed && <p className="eyebrow mb-3 px-3">Workspace</p>}
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = activeView === item.id
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                title={collapsed ? item.label : undefined}
                className={`group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-semibold transition ${
                  active ? 'bg-ink text-white shadow-[0_8px_18px_rgba(23,33,43,0.16)]' : 'text-slate-500 hover:bg-slate-100 hover:text-ink'
                } ${collapsed ? 'justify-center' : ''}`}
              >
                <Icon size={17} strokeWidth={active ? 2.2 : 1.8} />
                {!collapsed && <span className="flex-1">{item.label}</span>}
                {!collapsed && item.badge && (
                  <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.08em] ${active ? 'bg-white/15 text-white' : item.badge === 'live' ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {!collapsed && (
          <div className="mt-9">
            <p className="eyebrow mb-3 px-3">Intelligence</p>
            <div className="space-y-1.5">
              <div className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-semibold text-slate-400">
                <Target size={17} strokeWidth={1.8} />
                <span className="flex-1">Playbook memory</span>
                <span className="text-[9px] font-bold uppercase tracking-[0.08em]">Soon</span>
              </div>
              <div className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-semibold text-slate-400">
                <BarChart3 size={17} strokeWidth={1.8} />
                <span className="flex-1">Learning loop</span>
                <span className="text-[9px] font-bold uppercase tracking-[0.08em]">Soon</span>
              </div>
            </div>
          </div>
        )}

        <div className="mt-auto">
          {!collapsed && (
            <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-[11px] font-bold text-ink">Pod health</span>
                <span className="flex items-center gap-1.5 text-[10px] font-bold text-emerald-600">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 pulse-soft" /> Live
                </span>
              </div>
              <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full w-[86%] rounded-full bg-gradient-to-r from-emerald-400 to-emerald-600" />
              </div>
              <p className="text-[10px] leading-relaxed text-slate-400">CRM and supervisor are online. Signal stream is ready.</p>
            </div>
          )}
          <button onClick={onToggle} className={`icon-button w-full ${collapsed ? 'mx-auto' : 'justify-start gap-3 px-3'}`} title="Toggle sidebar">
            {collapsed ? <PanelLeftOpen size={17} /> : <><PanelLeftClose size={17} /><span className="text-xs font-semibold">Collapse sidebar</span></>}
          </button>
        </div>
      </div>
    </aside>
  )
}

function TopBar({
  onMobileMenu,
  onRefresh,
  refreshing,
  search,
  onSearchChange,
  onSearch,
}: {
  onMobileMenu: () => void
  onRefresh: () => void
  refreshing: boolean
  search: string
  onSearchChange: (value: string) => void
  onSearch: (event: FormEvent) => void
}) {
  return (
    <header className="sticky top-0 z-20 flex h-[82px] items-center justify-between border-b border-slate-200/70 bg-[#f8fafb]/90 px-5 backdrop-blur-xl md:px-8 lg:px-10">
      <div className="flex items-center gap-3">
        <button onClick={onMobileMenu} className="icon-button lg:hidden"><Menu size={19} /></button>
        <div className="lg:hidden"><Logo /></div>
        <div className="hidden items-center gap-2 text-xs text-slate-400 md:flex">
          <span className="font-semibold text-slate-500">Revenue workspace</span>
          <ChevronRight size={13} />
          <span>Command center</span>
        </div>
      </div>

      <div className="flex items-center gap-2.5 md:gap-4">
        <form onSubmit={onSearch} className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={15} />
          <input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search leads, accounts..."
            className="h-10 w-56 rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-xs font-medium text-ink outline-none transition placeholder:text-slate-400 focus:border-slate-300 focus:ring-4 focus:ring-slate-100 lg:w-64"
          />
        </form>
        <button onClick={onRefresh} className="icon-button" title="Refresh workspace" disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
        </button>
        <span className="icon-button relative" title="Notifications">
          <Bell size={17} />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-coral ring-2 ring-[#f8fafb]" />
        </span>
        <div className="hidden h-8 w-px bg-slate-200 sm:block" />
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#f0d8c9] text-[11px] font-extrabold text-[#9d5137]">SA</div>
          <div className="hidden text-left sm:block">
            <p className="text-xs font-bold text-ink">Siddhesh Asati</p>
            <p className="text-[10px] font-medium text-slate-400">Revenue lead</p>
          </div>
          <ChevronDown size={14} className="hidden text-slate-400 sm:block" />
        </div>
      </div>
    </header>
  )
}

function MetricCard({
  label,
  value,
  detail,
  icon,
  accent,
  trend,
}: {
  label: string
  value: string
  detail: string
  icon: ReactNode
  accent: string
  trend?: 'up' | 'down'
}) {
  return (
    <div className="card relative overflow-hidden p-5">
      <div className={`absolute -right-8 -top-10 h-28 w-28 rounded-full opacity-70 blur-2xl ${accent}`} />
      <div className="relative flex items-start justify-between">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-600">{icon}</span>
        {trend && (
          <span className={`flex items-center gap-0.5 text-[10px] font-bold ${trend === 'up' ? 'text-emerald-600' : 'text-rose-600'}`}>
            {trend === 'up' ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />} Live
          </span>
        )}
      </div>
      <div className="relative mt-5">
        <p className="eyebrow">{label}</p>
        <p className="mt-1.5 text-[25px] font-extrabold tracking-[-0.045em] text-ink">{value}</p>
        <p className="mt-1 text-[11px] font-medium text-slate-400">{detail}</p>
      </div>
    </div>
  )
}

function OverviewMetrics({ overview }: { overview: DashboardOverview }) {
  const totals = overview.pipeline_totals
  const coverage = totals.total_amount_minor ? totals.weighted_amount_minor / totals.total_amount_minor : 0
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Tracked pipeline"
        value={shortMoney(totals.total_amount_minor)}
        detail={`${totals.total_count} active deal records`}
        icon={<CircleDollarSign size={18} />}
        accent="bg-blue-200"
      />
      <MetricCard
        label="Weighted forecast"
        value={shortMoney(totals.weighted_amount_minor)}
        detail={`${Math.round(coverage * 100)}% probability-weighted coverage`}
        icon={<BarChart3 size={18} />}
        accent="bg-emerald-200"
        trend="up"
      />
      <MetricCard
        label="Deals at risk"
        value={`${overview.risk_counts.total}`}
        detail={`${overview.risk_counts.pending} waiting for manager review`}
        icon={<ShieldAlert size={18} />}
        accent="bg-amber-200"
        trend="down"
      />
      <MetricCard
        label="Pod activity"
        value={`${overview.recent_activities.length}`}
        detail="Latest CRM actions in the feed"
        icon={<Zap size={18} />}
        accent="bg-orange-200"
      />
    </div>
  )
}

function PipelineChart({ overview }: { overview: DashboardOverview }) {
  const data = overview.stage_summaries
    .filter((stage) => stage.stage !== 'closed_lost')
    .map((stage) => ({
      stage: stageLabel(stage.stage),
      amount: Math.round(stage.amount_minor / 100),
      weighted: Math.round(stage.weighted_amount_minor / 100),
    }))

  return (
    <div className="card min-h-[360px] p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Forecast shape</p>
          <h2 className="section-title mt-1.5 text-[17px]">Revenue coverage by stage</h2>
          <p className="muted mt-1 text-xs">Gross pipeline compared with probability-weighted value</p>
        </div>
        <span className="flex h-9 w-9 items-center justify-center text-slate-400"><MoreHorizontal size={18} /></span>
      </div>
      <div className="mt-7 h-[245px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barGap={5} margin={{ top: 8, right: 0, left: -18, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#edf0f3" />
            <XAxis dataKey="stage" axisLine={false} tickLine={false} tick={{ fill: '#9aa6b2', fontSize: 10 }} dy={9} />
            <YAxis axisLine={false} tickLine={false} tick={{ fill: '#a4afba', fontSize: 10 }} tickFormatter={(value) => `$${Math.round(value / 1000)}K`} />
            <Tooltip
              cursor={{ fill: '#f7f9fa' }}
              contentStyle={{ border: '1px solid #e7ebef', borderRadius: 12, fontSize: 11, boxShadow: '0 8px 24px rgba(31,50,68,.08)' }}
              formatter={(value: number, name: string) => [`$${value.toLocaleString()}`, name === 'amount' ? 'Gross' : 'Weighted']}
            />
            <Bar dataKey="amount" fill="#cad5df" radius={[5, 5, 0, 0]} maxBarSize={20} />
            <Bar dataKey="weighted" fill="#f36f4f" radius={[5, 5, 0, 0]} maxBarSize={20} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex items-center gap-5 text-[10px] font-semibold text-slate-400">
        <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-slate-300" /> Gross pipeline</span>
        <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-coral" /> Weighted value</span>
      </div>
    </div>
  )
}

function StageBreakdown({ overview, onOpenPipeline }: { overview: DashboardOverview; onOpenPipeline: () => void }) {
  const max = Math.max(...overview.stage_summaries.map((stage) => stage.amount_minor), 1)
  return (
    <div className="card p-5 sm:p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="eyebrow">Pipeline mix</p>
          <h2 className="section-title mt-1.5 text-[17px]">Stage breakdown</h2>
        </div>
        <button className="secondary-button px-3 py-2 text-[11px]" onClick={onOpenPipeline}><Filter size={13} /> Open pipeline</button>
      </div>
      <div className="mt-6 space-y-4">
        {overview.stage_summaries.map((stage) => (
          <div key={stage.stage}>
            <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
              <div className="flex min-w-0 items-center gap-2 font-semibold text-slate-600">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: stageColors[stage.stage] }} />
                <span className="truncate">{stageLabel(stage.stage)}</span>
              </div>
              <div className="flex shrink-0 items-center gap-2 text-[11px] font-bold text-ink">
                <span>{stage.count}</span><span className="font-medium text-slate-400">{shortMoney(stage.amount_minor)}</span>
              </div>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full transition-all" style={{ width: `${Math.max((stage.amount_minor / max) * 100, stage.count ? 3 : 0)}%`, backgroundColor: stageColors[stage.stage] }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-7 rounded-2xl border border-amber-100 bg-amber-50/70 p-3.5">
        <div className="flex gap-2.5">
          <AlertTriangle className="mt-0.5 shrink-0 text-amber-600" size={15} />
          <div>
            <p className="text-xs font-bold text-amber-900">Forecast watch</p>
            <p className="mt-1 text-[11px] leading-relaxed text-amber-800/75">Five negotiation deals have evidence of an unconfirmed economic buyer.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function ApprovalInbox({
  approvals,
  busyId,
  onSelect,
  onDecision,
  onReviewQueue,
}: {
  approvals: ApprovalRecord[]
  busyId: string | null
  onSelect: (approval: ApprovalRecord) => void
  onDecision: (approval: ApprovalRecord, decision: 'approved' | 'rejected') => void
  onReviewQueue: () => void
}) {
  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 p-5 sm:p-6">
        <div>
          <div className="flex items-center gap-2">
            <p className="eyebrow">Human in the loop</p>
            <span className="rounded-full bg-coral/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.1em] text-coral">Needs attention</span>
          </div>
          <h2 className="section-title mt-1.5 text-[17px]">Approval inbox</h2>
          <p className="muted mt-1 text-xs">Evidence-backed actions waiting for a manager decision</p>
        </div>
        <button className="secondary-button px-3 py-2 text-[11px]" onClick={onReviewQueue}>Review queue <ChevronRight size={13} /></button>
      </div>
      <div className="divide-y divide-slate-100">
        {approvals.slice(0, 4).map((approval) => (
          <div key={approval.id} className="group flex flex-col gap-4 px-5 py-4 transition hover:bg-slate-50/70 sm:flex-row sm:items-center sm:px-6">
            <button className="flex min-w-0 flex-1 items-center gap-3 text-left" onClick={() => onSelect(approval)}>
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600"><ShieldAlert size={18} /></div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="truncate text-sm font-bold text-ink">{approval.company_name}</p>
                  <StatusBadge status={approval.status} />
                </div>
                <p className="mt-1 truncate text-[11px] font-medium text-slate-400">{approval.deal_name} · {stageLabel(approval.deal_stage)} · {money(approval.amount_minor)}</p>
              </div>
            </button>
            <div className="flex items-center gap-2 sm:shrink-0">
              <span className="hidden text-[10px] font-medium text-slate-400 lg:block">{relativeDate(approval.created_at)}</span>
              {approval.status === 'pending' ? (
                <>
                  <button
                    onClick={() => onDecision(approval, 'rejected')}
                    disabled={busyId === approval.id}
                    className="rounded-lg border border-slate-200 px-2.5 py-2 text-[10px] font-bold text-slate-500 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => onDecision(approval, 'approved')}
                    disabled={busyId === approval.id}
                    className="rounded-lg bg-emerald-600 px-2.5 py-2 text-[10px] font-bold text-white transition hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {busyId === approval.id ? <Loader2 size={13} className="animate-spin" /> : 'Approve'}
                  </button>
                </>
              ) : (
                <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400"><CheckCircle2 size={14} className="text-emerald-500" /> Reviewed</span>
              )}
              <button className="icon-button h-8 w-8" onClick={() => onSelect(approval)}><ChevronRight size={15} /></button>
            </div>
          </div>
        ))}
      </div>
      {approvals.length > 4 && (
        <div className="border-t border-slate-100 px-5 py-3 text-center sm:px-6">
          <button className="text-[11px] font-bold text-coral hover:text-[#d95d3e]" onClick={onReviewQueue}>View all {approvals.length} evidence items</button>
        </div>
      )}
    </div>
  )
}

function ActivityFeed({ activities, onOpenAudit }: { activities: ActivitySummary[]; onOpenAudit: () => void }) {
  return (
    <div className="card p-5 sm:p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="eyebrow">Audit trail</p>
          <h2 className="section-title mt-1.5 text-[17px]">Pod activity</h2>
        </div>
        <span className="flex h-9 w-9 items-center justify-center text-slate-400"><MoreHorizontal size={18} /></span>
      </div>
      <div className="mt-5 space-y-1">
        {activities.slice(0, 6).map((activity) => (
          <div key={activity.id} className="flex gap-3 rounded-xl px-2 py-3 transition hover:bg-slate-50">
            <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">{activityIcon(activity.activity_type)}</div>
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-xs font-semibold leading-relaxed text-slate-600">{activity.body}</p>
              <div className="mt-1 flex items-center gap-2 text-[10px] font-medium text-slate-400"><span>{activity.actor}</span><span>·</span><span>{relativeDate(activity.occurred_at)}</span></div>
            </div>
          </div>
        ))}
      </div>
      <button onClick={onOpenAudit} className="mt-3 flex items-center gap-1 text-[11px] font-bold text-coral hover:text-[#d95d3e]">Open audit log <ArrowUpRight size={13} /></button>
    </div>
  )
}

function LeadSearch({
  leads,
  query,
  onQueryChange,
  onSubmit,
  loading,
}: {
  leads: LeadSummary[]
  query: string
  onQueryChange: (value: string) => void
  onSubmit: (event: FormEvent) => void
  loading: boolean
}) {
  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 p-5 sm:p-6">
        <div>
          <p className="eyebrow">Prioritization queue</p>
          <h2 className="section-title mt-1.5 text-[17px]">Leads to work next</h2>
          <p className="muted mt-1 text-xs">CRM search is ready for your next research motion</p>
        </div>
        <form onSubmit={onSubmit} className="relative w-full sm:w-56">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
          <input value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Search CRM" className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-8 pr-3 text-[11px] font-medium outline-none transition focus:border-slate-300 focus:bg-white" />
        </form>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left">
          <thead>
            <tr className="border-b border-slate-100 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
              <th className="px-5 py-3 font-bold sm:px-6">Lead</th>
              <th className="px-3 py-3 font-bold">Account</th>
              <th className="px-3 py-3 font-bold">Fit score</th>
              <th className="px-3 py-3 font-bold">Owner</th>
              <th className="px-5 py-3 text-right font-bold sm:px-6">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-10 text-center text-xs text-slate-400"><Loader2 size={17} className="mx-auto animate-spin" /></td></tr>
            ) : leads.map((lead) => (
              <tr key={lead.id} className="group transition hover:bg-slate-50/70">
                <td className="px-5 py-3.5 sm:px-6"><div className="flex items-center gap-2.5"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#e6edf3] text-[10px] font-extrabold text-navy">{initials(lead.name)}</div><div><p className="text-xs font-bold text-ink">{lead.name}</p><p className="mt-0.5 text-[10px] text-slate-400">{lead.title}</p></div></div></td>
                <td className="px-3 py-3.5 text-xs font-semibold text-slate-600">{lead.company_name}</td>
                <td className="px-3 py-3.5"><div className="flex items-center gap-2"><span className="text-xs font-extrabold text-ink">{lead.score}</span><span className="h-1.5 w-14 overflow-hidden rounded-full bg-slate-100"><span className="block h-full rounded-full bg-coral" style={{ width: `${lead.score}%` }} /></span></div></td>
                <td className="px-3 py-3.5 text-[11px] font-medium text-slate-500">{lead.owner}</td>
                <td className="px-5 py-3.5 text-right sm:px-6"><span className="rounded-full bg-slate-100 px-2 py-1 text-[9px] font-bold uppercase tracking-[0.08em] text-slate-500">{lead.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SupervisorPanel({
  messages,
  input,
  onInput,
  onSuggestion,
  onSubmit,
  loading,
}: {
  messages: Array<{ role: 'assistant' | 'user'; text: string }>
  input: string
  onInput: (value: string) => void
  onSuggestion: (value: string) => void
  onSubmit: (event: FormEvent) => void
  loading: boolean
}) {
  const suggestions = ['Why will we miss Q4?', 'Show current pipeline', 'Find leads at example.com']
  return (
    <div className="relative overflow-hidden rounded-[20px] bg-ink p-5 text-white shadow-[0_18px_40px_rgba(23,33,43,0.18)] sm:p-6">
      <div className="absolute -right-10 -top-14 h-44 w-44 rounded-full bg-coral/20 blur-3xl" />
      <div className="relative flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-orange-200"><Bot size={20} /></div>
          <div><p className="eyebrow text-slate-400">Supervisor console</p><h2 className="mt-1 text-[17px] font-bold tracking-[-0.02em]">Ask the pod</h2></div>
        </div>
        <span className="flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[9px] font-bold uppercase tracking-[0.1em] text-emerald-300"><span className="h-1.5 w-1.5 rounded-full bg-emerald-300 pulse-soft" /> online</span>
      </div>
      <div className="scrollbar-thin relative mt-6 max-h-[218px] space-y-3 overflow-y-auto pr-1">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-[11px] leading-relaxed ${message.role === 'user' ? 'rounded-br-md bg-coral text-white' : 'rounded-bl-md bg-white/10 text-slate-200'}`}>{message.text}</div>
          </div>
        ))}
        {loading && <div className="flex justify-start"><div className="rounded-2xl rounded-bl-md bg-white/10 px-3.5 py-2.5"><Loader2 size={14} className="animate-spin text-slate-300" /></div></div>}
      </div>
      <div className="relative mt-5 flex flex-wrap gap-1.5">
        {suggestions.map((suggestion) => <button key={suggestion} onClick={() => onSuggestion(suggestion)} className="rounded-full border border-white/10 px-2.5 py-1.5 text-[9px] font-semibold text-slate-300 transition hover:border-white/25 hover:text-white">{suggestion}</button>)}
      </div>
      <form onSubmit={onSubmit} className="relative mt-4 flex items-center gap-2 rounded-xl border border-white/10 bg-white/10 p-1.5 focus-within:border-white/25">
        <input value={input} onChange={(event) => onInput(event.target.value)} placeholder="Ask about your revenue..." className="min-w-0 flex-1 bg-transparent px-2 text-xs text-white outline-none placeholder:text-slate-500" />
        <button disabled={!input.trim() || loading} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-coral text-white transition hover:bg-[#dc6244] disabled:cursor-not-allowed disabled:opacity-50"><Send size={14} /></button>
      </form>
    </div>
  )
}

function DealDrawer({
  deal,
  approval,
  loading,
  onClose,
  onStageUpdate,
}: {
  deal: DealResponse | null
  approval: ApprovalRecord | null
  loading: boolean
  onClose: () => void
  onStageUpdate: (stage: DealStage, reason: string) => Promise<void>
}) {
  const [stage, setStage] = useState<DealStage>('negotiation')
  const [reason, setReason] = useState('Manager review updated the deal stage.')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (deal) setStage(deal.deal.stage)
  }, [deal])

  const saveStage = async () => {
    if (!deal || stage === deal.deal.stage || reason.trim().length < 3) return
    setSaving(true)
    try {
      await onStageUpdate(stage, reason)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-ink/20 backdrop-blur-[2px]" onClick={onClose}>
      <aside className="scrollbar-thin h-full w-full max-w-[480px] overflow-y-auto border-l border-slate-200 bg-[#fbfcfd] shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200/80 bg-[#fbfcfd]/95 px-5 py-4 backdrop-blur-xl sm:px-7">
          <div className="flex items-center gap-2"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 text-amber-600"><FileSearch size={16} /></span><span className="text-xs font-bold text-ink">Evidence trail</span></div>
          <button onClick={onClose} className="icon-button"><X size={18} /></button>
        </div>
        {loading || !deal ? (
          <div className="space-y-5 p-5 sm:p-7"><div className="h-5 w-2/3 animate-pulse rounded bg-slate-200" /><div className="h-28 animate-pulse rounded-2xl bg-slate-200" /><div className="h-52 animate-pulse rounded-2xl bg-slate-200" /></div>
        ) : (
          <div className="p-5 sm:p-7">
            <div className="flex items-start justify-between gap-3">
              <div><p className="eyebrow">Deal record</p><h2 className="mt-1.5 text-[20px] font-extrabold tracking-[-0.04em] text-ink">{deal.company.name}</h2><p className="mt-1 text-xs font-medium text-slate-400">{deal.company.domain}</p></div>
              <StageBadge stage={deal.deal.stage} />
            </div>
            <div className="mt-6 rounded-2xl bg-ink p-5 text-white">
              <p className="text-xs font-semibold text-slate-400">{deal.deal.name}</p>
              <div className="mt-3 flex items-end justify-between gap-3"><p className="text-[28px] font-extrabold tracking-[-0.05em]">{money(deal.deal.amount_minor, deal.deal.currency)}</p><p className="text-xs font-bold text-orange-200">{Math.round(deal.deal.probability * 100)}% probability</p></div>
              <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-coral" style={{ width: `${deal.deal.probability * 100}%` }} /></div>
              <div className="mt-4 flex items-center justify-between text-[10px] font-medium text-slate-400"><span>Close target</span><span className="font-bold text-slate-200">{formatDate(deal.deal.close_date)}</span></div>
            </div>

            <div className="mt-7 grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-slate-200 bg-white p-3"><p className="eyebrow">Owner</p><p className="mt-1.5 text-xs font-bold text-ink">{deal.deal.owner}</p></div>
              <div className="rounded-xl border border-slate-200 bg-white p-3"><p className="eyebrow">Industry</p><p className="mt-1.5 text-xs font-bold text-ink">{deal.company.industry}</p></div>
            </div>

            <div className="mt-7">
              {approval && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4">
                  <div className="flex items-center gap-2"><ShieldAlert size={15} className="text-amber-600" /><h3 className="text-sm font-bold text-amber-900">Why this is flagged</h3></div>
                  {approval.evidence.map((item) => <div key={item.source_id} className="mt-3"><p className="text-xs leading-relaxed text-amber-900/80">{item.summary}</p><p className="mt-1 text-[10px] font-medium text-amber-700/70">Call transcript · {formatDate(item.occurred_at)}</p></div>)}
                </div>
              )}
            </div>

            <div className="mt-7">
              <div className="mb-3 flex items-center justify-between"><h3 className="text-sm font-bold text-ink">Update stage</h3><span className="text-[10px] font-medium text-slate-400">Version {deal.deal.version}</span></div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <select value={stage} onChange={(event) => setStage(event.target.value as DealStage)} className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 text-xs font-semibold text-ink outline-none focus:border-slate-300">
                  {(Object.keys(stageLabels) as DealStage[]).map((value) => <option key={value} value={value}>{stageLabels[value]}</option>)}
                </select>
                <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={2} className="mt-2 w-full resize-none rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-ink outline-none focus:border-slate-300" />
                <button onClick={saveStage} disabled={saving || stage === deal.deal.stage || reason.trim().length < 3} className="primary-button mt-2 w-full py-2.5 text-xs">{saving ? <Loader2 size={14} className="animate-spin" /> : <><Check size={14} /> Save stage update</>}</button>
              </div>
            </div>

            <div className="mt-7">
              <h3 className="text-sm font-bold text-ink">Stage history</h3>
              <div className="mt-4 space-y-4 border-l border-slate-200 pl-4">
                {deal.stage_history.map((change) => <div key={change.id} className="relative"><span className="absolute -left-[21px] top-0.5 h-2.5 w-2.5 rounded-full border-2 border-[#fbfcfd] bg-coral ring-1 ring-coral/30" /><p className="text-xs font-bold text-ink">{change.from_stage ? `${stageLabel(change.from_stage)} → ` : ''}{stageLabel(change.to_stage)}</p><p className="mt-1 text-[10px] leading-relaxed text-slate-400">{change.reason}</p><p className="mt-1 text-[10px] font-medium text-slate-400">{change.actor} · {formatDate(change.occurred_at)}</p></div>)}
              </div>
            </div>

            <div className="mt-7">
              <h3 className="text-sm font-bold text-ink">Recent activity</h3>
              <div className="mt-3 space-y-2">{deal.recent_activities.slice(0, 4).map((activity) => <div key={activity.id} className="rounded-xl bg-white p-3"><div className="flex items-center justify-between"><span className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400">{activity.activity_type}</span><span className="text-[10px] text-slate-400">{relativeDate(activity.occurred_at)}</span></div><p className="mt-1.5 text-xs leading-relaxed text-slate-600">{activity.body}</p></div>)}</div>
            </div>
          </div>
        )}
      </aside>
    </div>
  )
}

function SignalBadge({ eventType }: { eventType: SignalEventType }) {
  if (eventType === 'funding_round') {
    return <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-700">Funding Round</span>
  }
  if (eventType === 'new_cto') {
    return <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-indigo-700">New CTO</span>
  }
  if (eventType === 'layoffs') {
    return <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-700">Layoffs</span>
  }
  if (eventType === 'tech_stack_change') {
    return <span className="rounded-full border border-purple-200 bg-purple-50 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-purple-700">Tech Stack</span>
  }
  if (eventType === 'leadership_change') {
    return <span className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-blue-700">Leadership</span>
  }
  return <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-slate-600">{eventType.replaceAll('_', ' ')}</span>
}

function SignalPipelineModal({
  signal,
  pipeline,
  loading,
  onClose,
  onApproveAndSend,
  busy,
}: {
  signal: SignalEventRecord | null
  pipeline: SignalPipelineResult | null
  loading: boolean
  onClose: () => void
  onApproveAndSend: (approvalId: string) => Promise<void>
  busy: boolean
}) {
  const [activeTab, setActiveTab] = useState<'variants' | 'committee' | 'research' | 'compliance'>('variants')
  const [selectedVariantIdx, setSelectedVariantIdx] = useState(0)

  if (!signal) return null

  const steps = [
    { title: 'Signal Event', sub: signal.event_type.replaceAll('_', ' '), done: true },
    { title: 'Account Research', sub: 'via signals-mcp', done: !!pipeline },
    { title: 'ICP Scoring', sub: 'Role weighted', done: !!pipeline },
    { title: 'Buying Committee', sub: 'Mapped', done: !!pipeline },
    { title: 'Email Variants', sub: '3 Angles', done: !!pipeline },
    { title: 'Compliance Check', sub: '100% Passed', done: !!pipeline?.compliance_check?.compliant },
    { title: 'Approval Inbox', sub: pipeline?.sandbox_send ? 'Approved' : 'Awaiting Review', done: !!pipeline },
    { title: 'Sandbox Send', sub: pipeline?.sandbox_send ? 'Delivered' : 'Pending Action', done: !!pipeline?.sandbox_send },
    { title: 'CRM Activity & Audit', sub: pipeline?.sandbox_send ? 'Recorded' : 'Pending Send', done: !!pipeline?.sandbox_send },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="scrollbar-thin max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl sm:p-8" onClick={(e) => e.stopPropagation()}>
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-coral/10 text-coral">
              <Sparkles size={22} />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="eyebrow text-coral">Autonomous Signal Radar Pipeline</span>
                <SignalBadge eventType={signal.event_type} />
              </div>
              <h2 className="mt-1 text-lg font-extrabold tracking-[-0.03em] text-ink sm:text-xl">{signal.headline}</h2>
              <p className="mt-1 text-xs text-slate-500">{signal.company_name} · {signal.company_domain} · Score {signal.relevance_score}/100</p>
            </div>
          </div>
          <button onClick={onClose} className="icon-button"><X size={18} /></button>
        </div>

        {/* 9-Stage Progress Stepper */}
        <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
          <p className="eyebrow text-slate-400">9-Stage Autonomous Flow Execution</p>
          <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5 md:grid-cols-9">
            {steps.map((st, i) => (
              <div key={st.title} className="flex flex-col items-center rounded-xl bg-white p-2 text-center shadow-xs border border-slate-200/60">
                <div className={`flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold ${st.done ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-500'}`}>
                  {st.done ? <Check size={12} /> : i + 1}
                </div>
                <p className="mt-1.5 text-[10px] font-bold leading-tight text-ink line-clamp-1">{st.title}</p>
                <p className="text-[9px] text-slate-400 line-clamp-1">{st.sub}</p>
              </div>
            ))}
          </div>
        </div>

        {loading || !pipeline ? (
          <div className="flex min-h-[300px] flex-col items-center justify-center space-y-3">
            <Loader2 className="animate-spin text-coral" size={32} />
            <p className="text-sm font-semibold text-ink">Executing autonomous research, committee mapping & compliance checks...</p>
            <p className="text-xs text-slate-400">Querying custom signals-mcp server and crafting personalized variants</p>
          </div>
        ) : (
          <div className="mt-6">
            {/* Tabs */}
            <div className="flex border-b border-slate-200">
              <button
                onClick={() => setActiveTab('variants')}
                className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-bold transition ${activeTab === 'variants' ? 'border-coral text-coral' : 'border-transparent text-slate-500 hover:text-ink'}`}
              >
                <Mail size={14} /> Email Variants ({pipeline.email_variants.length})
              </button>
              <button
                onClick={() => setActiveTab('committee')}
                className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-bold transition ${activeTab === 'committee' ? 'border-coral text-coral' : 'border-transparent text-slate-500 hover:text-ink'}`}
              >
                <Users size={14} /> Buying Committee
              </button>
              <button
                onClick={() => setActiveTab('research')}
                className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-bold transition ${activeTab === 'research' ? 'border-coral text-coral' : 'border-transparent text-slate-500 hover:text-ink'}`}
              >
                <FileSearch size={14} /> signals-mcp Intel
              </button>
              <button
                onClick={() => setActiveTab('compliance')}
                className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-bold transition ${activeTab === 'compliance' ? 'border-coral text-coral' : 'border-transparent text-slate-500 hover:text-ink'}`}
              >
                <ShieldCheck size={14} /> Compliance Clearance
              </button>
            </div>

            {/* Tab: Variants */}
            {activeTab === 'variants' && (
              <div className="mt-5 space-y-4">
                <div className="flex flex-wrap gap-2">
                  {pipeline.email_variants.map((v, idx) => (
                    <button
                      key={v.variant_id}
                      onClick={() => setSelectedVariantIdx(idx)}
                      className={`rounded-xl px-3 py-2 text-xs font-bold transition ${selectedVariantIdx === idx ? 'bg-ink text-white' : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`}
                    >
                      {v.name}
                    </button>
                  ))}
                </div>
                {pipeline.email_variants[selectedVariantIdx] && (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-5">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/60 pb-3">
                      <div>
                        <span className="eyebrow text-slate-400">Target Persona</span>
                        <p className="text-xs font-bold text-ink">{pipeline.email_variants[selectedVariantIdx].target_persona}</p>
                      </div>
                      <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-1 text-[10px] font-bold text-emerald-700">Angle: {pipeline.email_variants[selectedVariantIdx].angle}</span>
                    </div>
                    <div className="mt-3">
                      <p className="text-xs font-bold text-slate-700"><span className="text-slate-400">Subject:</span> {pipeline.email_variants[selectedVariantIdx].subject}</p>
                    </div>
                    <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4 text-xs font-medium leading-relaxed text-slate-700 whitespace-pre-line">
                      {pipeline.email_variants[selectedVariantIdx].body}
                    </div>
                    <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
                      <span>Call to Action: <strong className="text-ink">{pipeline.email_variants[selectedVariantIdx].call_to_action}</strong></span>
                      <span className="flex items-center gap-1 text-emerald-600 font-semibold"><ShieldCheck size={14} /> CAN-SPAM & Policy Cleared</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Tab: Committee */}
            {activeTab === 'committee' && (
              <div className="mt-5 grid gap-3 sm:grid-cols-2 md:grid-cols-3">
                {pipeline.buying_committee.economic_buyer && (
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4">
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-800">Economic Buyer</span>
                    <h4 className="mt-2 text-sm font-bold text-ink">{pipeline.buying_committee.economic_buyer.name}</h4>
                    <p className="text-xs text-slate-500">{pipeline.buying_committee.economic_buyer.title}</p>
                    <p className="mt-1 text-[11px] font-medium text-emerald-700">{pipeline.buying_committee.economic_buyer.email}</p>
                    <div className="mt-3 border-t border-emerald-200/50 pt-2 text-[10px] text-slate-500">
                      <strong className="text-ink">Fit Score {pipeline.buying_committee.economic_buyer.fit_score}/100</strong>: {pipeline.buying_committee.economic_buyer.rationale}
                    </div>
                  </div>
                )}
                {pipeline.buying_committee.technical_buyer && (
                  <div className="rounded-2xl border border-indigo-200 bg-indigo-50/50 p-4">
                    <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-indigo-800">Technical Buyer</span>
                    <h4 className="mt-2 text-sm font-bold text-ink">{pipeline.buying_committee.technical_buyer.name}</h4>
                    <p className="text-xs text-slate-500">{pipeline.buying_committee.technical_buyer.title}</p>
                    <p className="mt-1 text-[11px] font-medium text-indigo-700">{pipeline.buying_committee.technical_buyer.email}</p>
                    <div className="mt-3 border-t border-indigo-200/50 pt-2 text-[10px] text-slate-500">
                      <strong className="text-ink">Fit Score {pipeline.buying_committee.technical_buyer.fit_score}/100</strong>: {pipeline.buying_committee.technical_buyer.rationale}
                    </div>
                  </div>
                )}
                {pipeline.buying_committee.champion && (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-4">
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-800">Champion / User</span>
                    <h4 className="mt-2 text-sm font-bold text-ink">{pipeline.buying_committee.champion.name}</h4>
                    <p className="text-xs text-slate-500">{pipeline.buying_committee.champion.title}</p>
                    <p className="mt-1 text-[11px] font-medium text-amber-700">{pipeline.buying_committee.champion.email}</p>
                    <div className="mt-3 border-t border-amber-200/50 pt-2 text-[10px] text-slate-500">
                      <strong className="text-ink">Fit Score {pipeline.buying_committee.champion.fit_score}/100</strong>: {pipeline.buying_committee.champion.rationale}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Tab: Research */}
            {activeTab === 'research' && (
              <div className="mt-5 space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <p className="eyebrow text-slate-400">signals-mcp / get_tech_stack</p>
                  <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {Object.entries(pipeline.account_research.tech_stack?.technologies || {}).map(([cat, item]: any) => (
                      <div key={cat} className="rounded-xl border border-slate-100 bg-slate-50 p-2.5">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{cat.replaceAll('_', ' ')}</p>
                        <p className="mt-1 text-xs font-bold text-ink truncate">{item.name}</p>
                        <span className="text-[9px] capitalize text-slate-400">{item.status?.replaceAll('_', ' ')}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <p className="eyebrow text-slate-400">signals-mcp / get_company_news & get_funding_events</p>
                  <div className="mt-2 space-y-2">
                    {pipeline.account_research.recent_news.map((item, i) => (
                      <div key={i} className="rounded-xl border border-slate-100 bg-slate-50/70 p-3">
                        <div className="flex items-center justify-between text-[11px]"><strong className="text-ink">{item.title}</strong><span className="text-slate-400">{item.source}</span></div>
                        <p className="mt-1 text-xs text-slate-500">{item.summary}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Compliance */}
            {activeTab === 'compliance' && (
              <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50/30 p-5">
                <div className="flex items-center gap-2 text-emerald-800">
                  <ShieldCheck size={18} />
                  <h4 className="text-sm font-bold">Policy & Compliance Clearance</h4>
                  <span className="ml-auto rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800">Risk Score: 0.04 (Low)</span>
                </div>
                <p className="mt-2 text-xs text-slate-600">{pipeline.compliance_check.recommendation}</p>
                <div className="mt-4 divide-y divide-emerald-100 border-t border-emerald-100">
                  {pipeline.compliance_check.checks.map((chk, i) => (
                    <div key={i} className="flex items-center justify-between py-2.5 text-xs">
                      <span className="font-semibold text-slate-700 capitalize">{chk.rule.replaceAll('_', ' ')}</span>
                      <span className="text-slate-500">{chk.detail}</span>
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[9px] font-bold uppercase text-emerald-800">Pass</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Bottom Actions */}
            <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
              {pipeline.sandbox_send ? (
                <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-3.5 py-2 text-xs font-bold text-emerald-700 border border-emerald-200">
                  <CheckCircle2 size={16} /> Dispatched to Sandbox ({pipeline.sandbox_send.message_id}) · Activity & Audit Logged
                </div>
              ) : pipeline.approval_id ? (
                <button
                  onClick={() => onApproveAndSend(pipeline.approval_id!)}
                  disabled={busy}
                  className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-emerald-700 disabled:opacity-50"
                >
                  {busy ? <Loader2 size={14} className="animate-spin" /> : <SendHorizontal size={14} />} Approve & Send to Sandbox
                </button>
              ) : null}
              <button onClick={onClose} className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-600 hover:bg-slate-50">Done</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function SignalRadar({
  overview,
  signals,
  onAcknowledge,
  onSimulate,
  onSeedCohort,
  onRunPipeline,
  busyId,
  simulating,
}: {
  overview: DashboardOverview
  signals: SignalEventRecord[]
  onAcknowledge: (signal: SignalEventRecord) => void
  onSimulate: (eventType?: string) => Promise<void>
  onSeedCohort: () => Promise<void>
  onRunPipeline: (signal: SignalEventRecord) => Promise<void>
  busyId: string | null
  simulating: boolean
}) {
  const [selectedEventType, setSelectedEventType] = useState<string>('new_cto')

  return (
    <div className="card grid-pattern overflow-hidden p-5 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
            <Radio size={19} />
          </div>
          <div>
            <p className="eyebrow">Event-driven intelligence</p>
            <h2 className="section-title mt-1.5 text-[17px]">Signal radar</h2>
            <p className="muted mt-1 text-xs">Simulated event stream & autonomous GTM orchestration pipeline</p>
          </div>
        </div>
        
        {/* Interactive Event Stream Simulation Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedEventType}
            onChange={(e) => setSelectedEventType(e.target.value)}
            className="h-9 rounded-xl border border-slate-200 bg-white px-2.5 text-[11px] font-semibold text-ink outline-none"
          >
            <option value="funding_round">Funding Round</option>
            <option value="new_cto">New CTO</option>
            <option value="layoffs">Layoffs / Restructure</option>
            <option value="tech_stack">Tech Stack Change</option>
            <option value="leadership_change">Leadership Change</option>
          </select>
          <button
            onClick={() => onSimulate(selectedEventType)}
            disabled={simulating}
            className="flex items-center gap-1.5 rounded-xl bg-ink px-3 py-2 text-[11px] font-bold text-white transition hover:bg-slate-800 disabled:opacity-50"
          >
            {simulating ? <Loader2 size={12} className="animate-spin" /> : <Radio size={12} />} Simulate Event
          </button>
          <button
            onClick={() => onSeedCohort()}
            disabled={simulating}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-[11px] font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            <Sparkles size={12} className="text-coral" /> Seed 5-Event Cohort
          </button>
        </div>
      </div>

      <div className="mt-7 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
          <p className="eyebrow">Radar events</p>
          <p className="mt-2 text-2xl font-extrabold tracking-[-0.04em] text-ink">{signals.length}</p>
          <p className="mt-1 text-[11px] text-slate-400">Live events across target accounts</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
          <p className="eyebrow">New signals</p>
          <p className="mt-2 text-2xl font-extrabold tracking-[-0.04em] text-ink">
            {signals.filter((signal) => signal.status === 'new').length}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">Ready for autonomous workflow</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
          <p className="eyebrow">Avg relevance</p>
          <p className="mt-2 text-2xl font-extrabold tracking-[-0.04em] text-ink">
            {signals.length ? Math.round(signals.reduce((sum, signal) => sum + signal.relevance_score, 0) / signals.length) : 0}%
          </p>
          <p className="mt-1 text-[11px] text-slate-400">Weighted ICP relevance score</p>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {signals.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-xs text-slate-400">
            No signal events match the current view. Click "Simulate Event" above to inject a live signal.
          </div>
        ) : (
          signals.map((signal) => (
            <div key={signal.id} className="group rounded-2xl border border-slate-200/90 bg-white/90 p-4 transition hover:border-slate-300 hover:shadow-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <SignalBadge eventType={signal.event_type} />
                  <span className="text-xs font-bold text-ink">{signal.company_name}</span>
                  <span className="text-[11px] font-medium text-slate-400">· {signal.company_domain}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600">
                    Relevance {signal.relevance_score}%
                  </span>
                  <span className="text-[10px] font-medium text-slate-400">{relativeDate(signal.occurred_at)}</span>
                </div>
              </div>

              <h3 className="mt-2 text-sm font-bold text-ink">{signal.headline}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">{signal.summary}</p>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
                <div className="flex items-center gap-2 text-[11px] text-slate-500">
                  <span className="font-semibold text-slate-400">Suggested Motion:</span>
                  <span>{signal.suggested_action}</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onRunPipeline(signal)}
                    disabled={busyId === signal.id}
                    className="flex items-center gap-1.5 rounded-xl bg-coral px-3 py-1.5 text-[11px] font-bold text-white shadow-xs transition hover:bg-[#e05635] disabled:opacity-50"
                  >
                    {busyId === signal.id ? <Loader2 size={12} className="animate-spin" /> : <Play size={11} />} Run Pod Flow
                  </button>
                  {signal.status === 'new' ? (
                    <button
                      onClick={() => onAcknowledge(signal)}
                      disabled={busyId === signal.id}
                      className="rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-bold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                    >
                      Acknowledge
                    </button>
                  ) : (
                    <span className="rounded-lg bg-emerald-50 px-2 py-1 text-[10px] font-bold capitalize text-emerald-700 border border-emerald-200">
                      {signal.status}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-5 flex items-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-white/60 p-4">
        <Sparkles size={17} className="shrink-0 text-coral" />
        <p className="text-xs leading-relaxed text-slate-500">
          <span className="font-bold text-ink">Autonomous Signal Loop:</span> Click <strong>Run Pod Flow</strong> on any signal above to run the 9-stage sequence: Account research via <code>signals-mcp</code>, ICP scoring, buying committee mapping, personalized email drafts, compliance check, approval inbox enqueuing, and sandbox delivery.
        </p>
      </div>
    </div>
  )
}

function AuditLog({ events }: { events: AuditEventSummary[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-slate-100 p-5 sm:p-6"><p className="eyebrow">Immutable trail</p><h2 className="section-title mt-1.5 text-[17px]">Audit events</h2><p className="muted mt-1 text-xs">Every persisted approval and CRM mutation is visible here.</p></div>
      <div className="divide-y divide-slate-100">
        {events.length === 0 ? <div className="p-8 text-center text-xs text-slate-400">No audit events yet.</div> : events.map((event) => <div key={event.id} className="flex gap-3 px-5 py-4 sm:px-6"><div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500"><ShieldCheck size={15} /></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-bold text-ink">{event.event_type.replaceAll('.', ' ')}</p><span className="text-[10px] text-slate-400">{relativeDate(event.occurred_at)}</span></div><p className="mt-1 text-[11px] text-slate-500">{event.actor} · {event.entity_type} {event.entity_id}</p><pre className="mt-2 overflow-x-auto rounded-lg bg-slate-50 p-2 text-[10px] leading-relaxed text-slate-500">{JSON.stringify(event.payload)}</pre></div></div>)}
      </div>
    </div>
  )
}

function MobileNav({ activeView, onNavigate }: { activeView: View; onNavigate: (view: View) => void }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200/80 bg-white/95 px-2 py-2 shadow-[0_-8px_30px_rgba(23,33,43,0.08)] backdrop-blur-xl lg:hidden">
      <div className="mx-auto flex max-w-md items-center justify-around">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = activeView === item.id
          return <button key={item.id} onClick={() => onNavigate(item.id)} className={`relative flex min-w-[66px] flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[9px] font-bold ${active ? 'text-coral' : 'text-slate-400'}`}><Icon size={17} /><span>{item.label.split(' ')[0]}</span>{item.badge && <span className="absolute right-1 top-0.5 h-1.5 w-1.5 rounded-full bg-coral" />}</button>
        })}
      </div>
    </div>
  )
}

const emptyMessages: Array<{ role: 'assistant' | 'user'; text: string }> = [
  { role: 'assistant', text: 'I’m watching the pipeline. Ask me to surface risk, find a lead, or explain a forecast number.' },
]

export default function App() {
  const [activeView, setActiveView] = useState<View>('overview')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([])
  const [signals, setSignals] = useState<SignalEventRecord[]>([])
  const [auditEvents, setAuditEvents] = useState<AuditEventSummary[]>([])
  const [leads, setLeads] = useState<LeadSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRecord | null>(null)
  const [selectedDeal, setSelectedDeal] = useState<DealResponse | null>(null)
  const [dealLoading, setDealLoading] = useState(false)
  const [approvalBusy, setApprovalBusy] = useState<string | null>(null)
  const [signalBusy, setSignalBusy] = useState<string | null>(null)
  const [activePipelineSignal, setActivePipelineSignal] = useState<SignalEventRecord | null>(null)
  const [activePipelineResult, setActivePipelineResult] = useState<SignalPipelineResult | null>(null)
  const [pipelineLoading, setPipelineLoading] = useState(false)
  const [pipelineBusy, setPipelineBusy] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const [leadQuery, setLeadQuery] = useState('')
  const [leadSearchLoading, setLeadSearchLoading] = useState(false)
  const [headerSearch, setHeaderSearch] = useState('')
  const [agentInput, setAgentInput] = useState('')
  const [agentLoading, setAgentLoading] = useState(false)
  const [agentMessages, setAgentMessages] = useState(emptyMessages)

  const loadWorkspace = useCallback(async (initial = false) => {
    if (initial) setLoading(true)
    else setRefreshing(true)
    setError(null)
    try {
      const [overviewResult, approvalsResult, leadsResult, signalsResult] = await Promise.all([
        api.getOverview(),
        api.getApprovals(),
        api.searchLeads(''),
        api.getSignals(),
      ])
      setOverview(overviewResult)
      setApprovals(approvalsResult)
      setSignals(signalsResult)
      setLeads(leadsResult.items)
      setAuditEvents(overviewResult.recent_audit_events)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load the revenue workspace.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void loadWorkspace(true)
  }, [loadWorkspace])

  useEffect(() => {
    if (activeView !== 'audit') return
    void api
      .getAuditEvents()
      .then(setAuditEvents)
      .catch((cause: unknown) => {
        setError(cause instanceof Error ? cause.message : 'Unable to load the audit log.')
      })
  }, [activeView])

  const handleNavigate = (view: View) => {
    setActiveView(view)
    setMobileOpen(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault()
    setLeadQuery(headerSearch)
    setActiveView('overview')
    setLeadSearchLoading(true)
    setError(null)
    try {
      const result = await api.searchLeads(headerSearch)
      setLeads(result.items)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Lead search failed.')
    } finally {
      setLeadSearchLoading(false)
    }
  }

  const handleLeadSearch = async (event: FormEvent) => {
    event.preventDefault()
    setLeadSearchLoading(true)
    setError(null)
    try {
      const result = await api.searchLeads(leadQuery)
      setLeads(result.items)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Lead search failed.')
    } finally {
      setLeadSearchLoading(false)
    }
  }

  const handleSelectApproval = async (approval: ApprovalRecord) => {
    setSelectedApproval(approval)
    setSelectedDeal(null)
    setDealLoading(true)
    try {
      const result = await api.getDeal(approval.deal_id)
      setSelectedDeal(result)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load deal evidence.')
    } finally {
      setDealLoading(false)
    }
  }

  const handleDecision = async (approval: ApprovalRecord, decision: 'approved' | 'rejected') => {
    setApprovalBusy(approval.id)
    setError(null)
    try {
      const result = await api.decideApproval(approval.id, decision, `Reviewed in the command center.`)
      setApprovals((current) => current.map((item) => (item.id === result.id ? result : item)))
      const refreshedOverview = await api.getOverview()
      setOverview(refreshedOverview)
      setAuditEvents(refreshedOverview.recent_audit_events)
      if (selectedApproval?.id === result.id) setSelectedApproval(result)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to save the approval decision.')
    } finally {
      setApprovalBusy(null)
    }
  }

  const handleAcknowledgeSignal = async (signal: SignalEventRecord) => {
    setSignalBusy(signal.id)
    setError(null)
    try {
      const updated = await api.acknowledgeSignal(signal.id)
      setSignals((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to acknowledge the signal.')
    } finally {
      setSignalBusy(null)
    }
  }

  const handleSimulate = async (eventType?: string) => {
    setSimulating(true)
    setError(null)
    try {
      const newSignal = await api.simulateSignal(eventType)
      setSignals((current) => [newSignal, ...current])
      const refreshedOverview = await api.getOverview()
      setOverview(refreshedOverview)
      setAuditEvents(refreshedOverview.recent_audit_events)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Failed to simulate signal.')
    } finally {
      setSimulating(false)
    }
  }

  const handleSeedCohort = async () => {
    setSimulating(true)
    setError(null)
    try {
      const res = await api.seedStreamCohort()
      setSignals(res)
      const refreshedOverview = await api.getOverview()
      setOverview(refreshedOverview)
      setAuditEvents(refreshedOverview.recent_audit_events)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Failed to seed signal cohort.')
    } finally {
      setSimulating(false)
    }
  }

  const handleRunPipeline = async (signal: SignalEventRecord) => {
    setActivePipelineSignal(signal)
    setActivePipelineResult(null)
    setPipelineLoading(true)
    setError(null)
    try {
      const result = await api.runSignalPipeline(signal.id)
      setActivePipelineResult(result)
      setSignals((current) =>
        current.map((s) => (s.id === signal.id ? { ...s, status: 'processed' } : s))
      )
      const [refreshedApprovals, refreshedOverview] = await Promise.all([
        api.getApprovals(),
        api.getOverview(),
      ])
      setApprovals(refreshedApprovals)
      setOverview(refreshedOverview)
      setAuditEvents(refreshedOverview.recent_audit_events)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Failed to execute signal pipeline.')
    } finally {
      setPipelineLoading(false)
    }
  }

  const handleApproveAndSendSandbox = async (approvalId: string) => {
    setPipelineBusy(true)
    setError(null)
    try {
      const decided = await api.decideApproval(
        approvalId,
        'approved',
        'Approved from Signal Pipeline Modal & auto-dispatched to sandbox.'
      )
      setApprovals((current) => current.map((item) => (item.id === decided.id ? decided : item)))
      const [refreshedOverview, refreshedSignals] = await Promise.all([
        api.getOverview(),
        api.getSignals(),
      ])
      setOverview(refreshedOverview)
      setSignals(refreshedSignals)
      setAuditEvents(refreshedOverview.recent_audit_events)

      if (activePipelineResult) {
        setActivePipelineResult({
          ...activePipelineResult,
          sandbox_send: {
            status: 'sent',
            recipient: activePipelineResult.buying_committee.economic_buyer?.email || 'contact@target.com',
            subject: activePipelineResult.email_variants[0]?.subject || 'Partnership Inquiry',
            message_id: `sandbox-${Date.now().toString(36)}`,
            sent_at: new Date().toISOString(),
            sandbox_transport: 'mock_smtp_sandbox',
          },
        })
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Failed to approve and send to sandbox.')
    } finally {
      setPipelineBusy(false)
    }
  }

  const handleAskAgent = async (event: FormEvent) => {
    event.preventDefault()
    await askAgent(agentInput.trim())
  }

  const askAgent = async (prompt: string) => {
    if (!prompt || agentLoading) return
    setAgentInput('')
    setAgentMessages((current) => [...current, { role: 'user', text: prompt }])
    setAgentLoading(true)
    try {
      const result = await api.askAgent(prompt)
      setAgentMessages((current) => [...current, { role: 'assistant', text: result.response || result.errors[0] || 'No response was produced.' }])
    } catch (cause) {
      setAgentMessages((current) => [...current, { role: 'assistant', text: cause instanceof Error ? cause.message : 'The supervisor is unavailable.' }])
    } finally {
      setAgentLoading(false)
    }
  }

  const handleSuggestion = (prompt: string) => {
    void askAgent(prompt)
  }

  const handleStageUpdate = async (stage: DealStage, reason: string) => {
    if (!selectedDeal) return
    setError(null)
    try {
      await api.updateStage(selectedDeal.deal.id, { new_stage: stage, reason, expected_version: selectedDeal.deal.version })
      setSelectedDeal(await api.getDeal(selectedDeal.deal.id))
      await loadWorkspace()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to update the deal stage.')
    }
  }

  const pageCopy = useMemo(() => {
    if (activeView === 'pipeline') return { eyebrow: 'Pipeline command', title: 'See the shape of your quarter.', subtitle: 'Weighted coverage, stage friction, and the deals that need a sharper next step.' }
    if (activeView === 'approvals') return { eyebrow: 'Human in the loop', title: 'Keep autonomy accountable.', subtitle: 'Review evidence-backed decisions before they become customer-facing actions.' }
    if (activeView === 'signals') return { eyebrow: 'Event-driven intelligence', title: 'Signals before the meeting.', subtitle: 'Real-time corporate events driving autonomous research, committee mapping, and personalized outreach.' }
    if (activeView === 'audit') return { eyebrow: 'Immutable trail', title: 'See what the pod changed.', subtitle: 'Every persisted approval and CRM mutation has a traceable actor, entity, and payload.' }
    return { eyebrow: todayLabel(), title: 'Good morning, Siddhesh.', subtitle: 'Your pod is online. Here is what changed while you were away.' }
  }, [activeView])

  const content = overview ? (
    <>
      {(activeView === 'overview' || activeView === 'pipeline') && <OverviewMetrics overview={overview} />}
      {(activeView === 'overview' || activeView === 'pipeline') && (
        <div className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.65fr]"><PipelineChart overview={overview} /><StageBreakdown overview={overview} onOpenPipeline={() => handleNavigate('pipeline')} /></div>
      )}
      {(activeView === 'overview' || activeView === 'approvals') && (
        <div className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.65fr]"><ApprovalInbox approvals={approvals} busyId={approvalBusy} onSelect={handleSelectApproval} onDecision={handleDecision} onReviewQueue={() => handleNavigate('approvals')} /><ActivityFeed activities={overview.recent_activities} onOpenAudit={() => handleNavigate('audit')} /></div>
      )}
      {activeView === 'overview' && <div className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.65fr]"><LeadSearch leads={leads} query={leadQuery} onQueryChange={setLeadQuery} onSubmit={handleLeadSearch} loading={leadSearchLoading} /><SupervisorPanel messages={agentMessages} input={agentInput} onInput={setAgentInput} onSuggestion={handleSuggestion} onSubmit={handleAskAgent} loading={agentLoading} /></div>}
      {activeView === 'pipeline' && <div className="mt-5"><LeadSearch leads={leads} query={leadQuery} onQueryChange={setLeadQuery} onSubmit={handleLeadSearch} loading={leadSearchLoading} /></div>}
      {activeView === 'approvals' && <div className="mt-5"><SupervisorPanel messages={agentMessages} input={agentInput} onInput={setAgentInput} onSuggestion={handleSuggestion} onSubmit={handleAskAgent} loading={agentLoading} /></div>}
      {activeView === 'signals' && (
        <>
          <SignalRadar
            overview={overview}
            signals={signals}
            onAcknowledge={handleAcknowledgeSignal}
            onSimulate={handleSimulate}
            onSeedCohort={handleSeedCohort}
            onRunPipeline={handleRunPipeline}
            busyId={signalBusy}
            simulating={simulating}
          />
          <div className="mt-5">
            <ActivityFeed activities={overview.recent_activities} onOpenAudit={() => handleNavigate('audit')} />
          </div>
        </>
      )}
      {activeView === 'audit' && <AuditLog events={auditEvents} />}
    </>
  ) : (
    <div className="card flex min-h-[420px] items-center justify-center"><Loader2 className="animate-spin text-coral" size={24} /></div>
  )

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <Sidebar activeView={activeView} onNavigate={handleNavigate} collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      {mobileOpen && <div className="fixed inset-0 z-40 bg-ink/20 lg:hidden" onClick={() => setMobileOpen(false)}><div className="h-full w-[270px] bg-white p-5 shadow-2xl" onClick={(event) => event.stopPropagation()}><div className="mb-8 flex items-center justify-between"><Logo /><button onClick={() => setMobileOpen(false)} className="icon-button"><X size={18} /></button></div><nav className="space-y-1.5">{navItems.map((item) => { const Icon = item.icon; return <button key={item.id} onClick={() => handleNavigate(item.id)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold ${activeView === item.id ? 'bg-ink text-white' : 'text-slate-500'}`}><Icon size={17} />{item.label}</button> })}</nav></div></div>}
      <main className={`min-h-screen transition-all duration-300 ${collapsed ? 'lg:pl-[82px]' : 'lg:pl-[254px]'}`}>
        <TopBar onMobileMenu={() => setMobileOpen(true)} onRefresh={() => void loadWorkspace()} refreshing={refreshing} search={headerSearch} onSearchChange={setHeaderSearch} onSearch={handleSearch} />
        <div className="mx-auto max-w-[1480px] px-5 pb-28 pt-7 md:px-8 md:pt-9 lg:px-10 lg:pb-12">
          <div className="mb-7 flex flex-wrap items-end justify-between gap-5">
            <div><p className="eyebrow text-coral">{pageCopy.eyebrow}</p><h1 className="mt-2 text-[28px] font-extrabold tracking-[-0.055em] text-ink sm:text-[34px]">{pageCopy.title}</h1><p className="mt-2 max-w-2xl text-sm text-slate-500">{pageCopy.subtitle}</p></div>
            <div className="flex items-center gap-2"><span className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-2 text-[10px] font-bold text-emerald-700 sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500 pulse-soft" /> Pod live</span><button onClick={() => void loadWorkspace()} className="secondary-button px-3 py-2 text-[11px]"><RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} /> Sync CRM</button></div>
          </div>
          {error && <div className="mb-5 flex items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs font-medium text-rose-700"><AlertTriangle size={16} /><span className="flex-1">{error}</span><button onClick={() => setError(null)}><X size={15} /></button></div>}
          {loading ? <div className="space-y-5"><div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">{[1, 2, 3, 4].map((item) => <div key={item} className="h-[145px] animate-pulse rounded-[20px] bg-white" />)}</div><div className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]"><div className="h-[360px] animate-pulse rounded-[20px] bg-white" /><div className="h-[360px] animate-pulse rounded-[20px] bg-white" /></div></div> : content}
        </div>
      </main>
      <MobileNav activeView={activeView} onNavigate={handleNavigate} />
      {(selectedApproval || dealLoading) && <DealDrawer deal={selectedDeal} approval={selectedApproval} loading={dealLoading} onClose={() => { setSelectedApproval(null); setSelectedDeal(null) }} onStageUpdate={handleStageUpdate} />}
      {activePipelineSignal && (
        <SignalPipelineModal
          signal={activePipelineSignal}
          pipeline={activePipelineResult}
          loading={pipelineLoading}
          busy={pipelineBusy}
          onClose={() => {
            setActivePipelineSignal(null)
            setActivePipelineResult(null)
          }}
          onApproveAndSend={handleApproveAndSendSandbox}
        />
      )}
    </div>
  )
}
