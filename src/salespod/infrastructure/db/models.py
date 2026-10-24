from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("domain", name="uq_companies_domain"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(120), nullable=False)
    employee_band: Mapped[str] = mapped_column(String(40), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("email", name="uq_leads_email"),
        Index("ix_leads_company_id", "company_id"),
        Index("ix_leads_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        Index("ix_deals_company_id", "company_id"),
        Index("ix_deals_stage", "stage"),
        Index("ix_deals_close_date", "close_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    primary_lead_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("leads.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    close_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stage_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class EmailThread(Base):
    __tablename__ = "email_threads"
    __table_args__ = (
        Index("ix_email_threads_company_id", "company_id"),
        Index("ix_email_threads_lead_id", "lead_id"),
        Index("ix_email_threads_last_message_at", "last_message_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    reply_status: Mapped[str] = mapped_column(String(30), nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CallTranscript(Base):
    __tablename__ = "call_transcripts"
    __table_args__ = (
        Index("ix_call_transcripts_company_id", "company_id"),
        Index("ix_call_transcripts_lead_id", "lead_id"),
        Index("ix_call_transcripts_deal_id", "deal_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id"), nullable=False)
    deal_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("deals.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_steps: Mapped[str] = mapped_column(Text, nullable=False)


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_activities_idempotency_key"),
        Index("ix_activities_deal_id", "deal_id"),
        Index("ix_activities_occurred_at", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=True
    )
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), nullable=True)
    deal_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("deals.id"), nullable=True)
    activity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DealStageHistory(Base):
    __tablename__ = "deal_stage_history"
    __table_args__ = (Index("ix_stage_history_deal_id", "deal_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    deal_id: Mapped[str] = mapped_column(String(36), ForeignKey("deals.id"), nullable=False)
    from_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        UniqueConstraint("risk_type", "source_id", name="uq_approval_requests_risk_source"),
        Index("ix_approval_requests_status", "status"),
        Index("ix_approval_requests_deal_id", "deal_id"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    risk_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    deal_id: Mapped[str] = mapped_column(String(36), ForeignKey("deals.id"), nullable=False)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_occurred_at", "occurred_at"),
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
