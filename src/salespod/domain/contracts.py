from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import ActivityType, DealStage, LeadStatus, SignalEventType, SignalStatus


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchLeadsRequest(Contract):
    query: str | None = None
    company_id: UUID | None = None
    status: LeadStatus | None = None
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None


class LeadSummary(Contract):
    id: UUID
    company_id: UUID
    company_name: str
    name: str
    title: str
    email: str
    status: LeadStatus
    score: int = Field(ge=0, le=100)
    owner: str


class SearchLeadsResponse(Contract):
    items: list[LeadSummary]
    next_cursor: str | None = None
    total_estimate: int


class CompanySummary(Contract):
    id: UUID
    name: str
    domain: str
    industry: str
    employee_band: str
    region: str


class ActivitySummary(Contract):
    id: UUID
    activity_type: ActivityType
    body: str
    actor: str
    occurred_at: datetime
    company_id: UUID | None = None
    lead_id: UUID | None = None
    deal_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StageChange(Contract):
    id: UUID
    deal_id: UUID
    from_stage: DealStage | None
    to_stage: DealStage
    reason: str
    actor: str
    occurred_at: datetime


class DealDetail(Contract):
    id: UUID
    company_id: UUID
    primary_lead_id: UUID | None
    name: str
    stage: DealStage
    amount_minor: int = Field(ge=0)
    currency: str
    close_date: datetime
    probability: float = Field(ge=0, le=1)
    owner: str
    version: int = Field(ge=1)


class GetDealResponse(Contract):
    deal: DealDetail
    company: CompanySummary
    primary_lead: LeadSummary | None
    recent_activities: list[ActivitySummary]
    stage_history: list[StageChange]


class UpdateStageRequest(Contract):
    deal_id: UUID
    new_stage: DealStage
    reason: str = Field(min_length=3, max_length=500)
    actor: str = Field(min_length=1, max_length=120)
    expected_version: int = Field(ge=1)
    idempotency_key: str | None = Field(default=None, max_length=200)


class UpdateStageResponse(Contract):
    deal: DealDetail
    stage_change: StageChange


class LogActivityRequest(Contract):
    activity_type: ActivityType
    body: str = Field(min_length=1, max_length=10_000)
    actor: str = Field(min_length=1, max_length=120)
    occurred_at: datetime | None = None
    company_id: UUID | None = None
    lead_id: UUID | None = None
    deal_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        return value


class LogActivityResponse(Contract):
    activity: ActivitySummary


class PipelineStageSummary(Contract):
    stage: DealStage
    count: int = Field(ge=0)
    amount_minor: int = Field(ge=0)
    weighted_amount_minor: int = Field(ge=0)


class PipelineSnapshotResponse(Contract):
    generated_at: datetime
    currency: str
    stages: list[PipelineStageSummary]
    total_count: int = Field(ge=0)
    total_amount_minor: int = Field(ge=0)
    weighted_amount_minor: int = Field(ge=0)


class ListSignalsRequest(Contract):
    company_id: UUID | None = None
    event_type: SignalEventType | None = None
    status: SignalStatus | None = None
    query: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class SignalEventSummary(Contract):
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
