from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from salespod.application.policy import ActionKind, PolicyOutcome
from salespod.domain.contracts import ActivitySummary, PipelineStageSummary
from salespod.domain.enums import DealStage, SignalEventType, SignalStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HealthResponse(ApiModel):
    status: Literal["ok"]
    database: Literal["ok"]


class DashboardPipelineTotals(ApiModel):
    currency: str
    total_count: int = Field(ge=0)
    total_amount_minor: int = Field(ge=0)
    weighted_amount_minor: int = Field(ge=0)


class DashboardRiskCounts(ApiModel):
    total: int = Field(ge=0)
    pending: int = Field(ge=0)
    approved: int = Field(ge=0)
    rejected: int = Field(ge=0)
    by_type: dict[str, int] = Field(default_factory=dict)


class AuditEventSummary(ApiModel):
    id: UUID
    event_type: str
    actor: str
    entity_type: str
    entity_id: str
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class DashboardOverview(ApiModel):
    generated_at: datetime
    pipeline_totals: DashboardPipelineTotals
    stage_summaries: list[PipelineStageSummary]
    risk_counts: DashboardRiskCounts
    recent_activities: list[ActivitySummary]
    recent_audit_events: list[AuditEventSummary]


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalEvidence(ApiModel):
    source_id: UUID
    source_type: Literal["call_transcript"]
    summary: str
    occurred_at: datetime


class ApprovalRecord(ApiModel):
    id: str
    risk_type: Literal["missing_economic_buyer"]
    status: ApprovalStatus
    deal_id: UUID
    company_id: UUID
    company_name: str
    deal_name: str
    deal_stage: str
    amount_minor: int = Field(ge=0)
    created_at: datetime
    evidence: list[ApprovalEvidence]
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision_note: str | None = None


class ApprovalDecisionRequest(ApiModel):
    decision: ApprovalDecision
    actor: str = Field(min_length=1, max_length=120)
    note: str | None = Field(default=None, min_length=1, max_length=500)


class PolicyEvaluationRequest(ApiModel):
    action: ActionKind
    discount_percent: float | None = Field(default=None, ge=0, le=100)
    executive_outreach: bool = False


class PolicyEvaluationResponse(ApiModel):
    action: ActionKind
    outcome: PolicyOutcome
    reason: str
    threshold: str | None = None


class ErrorResponse(ApiModel):
    code: str
    message: str


class AgentAskRequest(ApiModel):
    request: str = Field(min_length=1, max_length=5_000)
    actor: str = Field(default="manager", min_length=1, max_length=120)


class AgentAskResponse(ApiModel):
    request: str
    actor: str
    trace_id: str
    intent: str | None = None
    tool_name: str | None = None
    response: str
    observations: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class StageChangeRequest(ApiModel):
    new_stage: DealStage
    reason: str = Field(min_length=3, max_length=500)
    actor: str = Field(min_length=1, max_length=120)
    expected_version: int = Field(ge=1)
    idempotency_key: str | None = Field(default=None, max_length=200)


class SignalEventRecord(ApiModel):
    id: UUID
    company_id: UUID
    company_name: str
    company_domain: str
    event_type: SignalEventType
    headline: str
    summary: str
    source: str
    source_url: str | None = None
    occurred_at: datetime
    status: SignalStatus
    relevance_score: int = Field(ge=0, le=100)
    suggested_action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SignalAcknowledgeRequest(ApiModel):
    actor: str = Field(min_length=1, max_length=120)
    note: str | None = Field(default=None, min_length=1, max_length=500)
