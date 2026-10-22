from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from salespod.domain.errors import ConflictError, NotFoundError
from salespod.infrastructure.db.models import CallTranscript, Company, Deal

from .schemas import (
    ApprovalDecision,
    ApprovalDecisionRequest,
    ApprovalEvidence,
    ApprovalRecord,
    ApprovalStatus,
    DashboardRiskCounts,
)

RISK_TYPE = "missing_economic_buyer"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class StoredDecision:
    decision: ApprovalDecision
    actor: str
    note: str | None
    decided_at: datetime


class ApprovalRepository:
    """Derive approval candidates from CRM evidence and retain decisions in memory.

    The candidate ID is derived from the planted call-transcript ID, so the list is
    stable across requests and contains no dashboard-only records. Decisions are
    process-local for this first API slice; a database table can replace the
    decision map without changing the HTTP contract.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self._decisions: dict[str, StoredDecision] = {}

    def list(self) -> list[ApprovalRecord]:
        with self.session_factory() as session:
            calls = session.scalars(
                select(CallTranscript)
                .where(
                    or_(
                        func.lower(CallTranscript.summary).like("%economic buyer%"),
                        func.lower(CallTranscript.transcript).like("%economic buyer%"),
                    )
                )
                .order_by(CallTranscript.occurred_at.desc(), CallTranscript.id)
            ).all()
            records: list[ApprovalRecord] = []
            for call in calls:
                deal = session.scalar(
                    select(Deal)
                    .where(Deal.primary_lead_id == call.lead_id)
                    .order_by(Deal.id)
                )
                if deal is None:
                    continue
                company = session.get(Company, deal.company_id)
                if company is None:
                    continue
                records.append(self._record(call, deal, company))
            return records

    def decide(self, approval_id: str, request: ApprovalDecisionRequest) -> ApprovalRecord:
        record = next((item for item in self.list() if item.id == approval_id), None)
        if record is None:
            raise NotFoundError(f"approval {approval_id} was not found")

        existing = self._decisions.get(approval_id)
        if existing is not None and existing.decision != request.decision:
            raise ConflictError(f"approval {approval_id} already has a decision")
        if existing is None:
            existing = StoredDecision(
                decision=request.decision,
                actor=request.actor,
                note=request.note,
                decided_at=datetime.now(UTC),
            )
            self._decisions[approval_id] = existing
        return record.model_copy(
            update={
                "status": ApprovalStatus(existing.decision.value),
                "decided_at": existing.decided_at,
                "decided_by": existing.actor,
                "decision_note": existing.note,
            }
        )

    def risk_counts(self) -> DashboardRiskCounts:
        records = self.list()
        by_type: dict[str, int] = {}
        for record in records:
            by_type[record.risk_type] = by_type.get(record.risk_type, 0) + 1
        return DashboardRiskCounts(
            total=len(records),
            pending=sum(record.status == ApprovalStatus.PENDING for record in records),
            approved=sum(record.status == ApprovalStatus.APPROVED for record in records),
            rejected=sum(record.status == ApprovalStatus.REJECTED for record in records),
            by_type=by_type,
        )

    def _record(self, call: CallTranscript, deal: Deal, company: Company) -> ApprovalRecord:
        approval_id = f"risk-{call.id}"
        stored = self._decisions.get(approval_id)
        return ApprovalRecord(
            id=approval_id,
            risk_type=RISK_TYPE,
            status=ApprovalStatus(stored.decision.value) if stored else ApprovalStatus.PENDING,
            deal_id=UUID(deal.id),
            company_id=UUID(deal.company_id),
            company_name=company.name,
            deal_name=deal.name,
            deal_stage=deal.stage,
            amount_minor=deal.amount_minor,
            created_at=_utc(call.occurred_at),
            evidence=[
                ApprovalEvidence(
                    source_id=UUID(call.id),
                    source_type="call_transcript",
                    summary=call.summary,
                    occurred_at=_utc(call.occurred_at),
                )
            ],
            decided_at=stored.decided_at if stored else None,
            decided_by=stored.actor if stored else None,
            decision_note=stored.note if stored else None,
        )
