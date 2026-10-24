from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from salespod.domain.errors import ConflictError, NotFoundError
from salespod.infrastructure.db.models import (
    ApprovalRequest,
    AuditEvent,
    CallTranscript,
    Company,
    Deal,
)
from salespod.infrastructure.db.repositories import new_uuid

from .schemas import (
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


class ApprovalRepository:
    """Persist evidence-backed approval requests and their decisions."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def list(self) -> list[ApprovalRecord]:
        with self.session_factory() as session:
            with session.begin():
                self._sync_candidates(session)
            rows = session.execute(
                select(ApprovalRequest, CallTranscript, Deal, Company)
                .join(CallTranscript, CallTranscript.id == ApprovalRequest.source_id)
                .join(Deal, Deal.id == ApprovalRequest.deal_id)
                .join(Company, Company.id == ApprovalRequest.company_id)
                .where(ApprovalRequest.risk_type == RISK_TYPE)
                .order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id)
            ).all()
            return [
                self._record(approval, call, deal, company)
                for approval, call, deal, company in rows
            ]

    def decide(self, approval_id: str, request: ApprovalDecisionRequest) -> ApprovalRecord:
        with self.session_factory() as session:
            with session.begin():
                self._sync_candidates(session)
                approval = session.get(ApprovalRequest, approval_id)
                if approval is None:
                    raise NotFoundError(f"approval {approval_id} was not found")
                if approval.status != ApprovalStatus.PENDING.value:
                    if approval.status != request.decision.value:
                        raise ConflictError(f"approval {approval_id} already has a decision")
                else:
                    approval.status = request.decision.value
                    approval.decided_at = datetime.now(UTC)
                    approval.decided_by = request.actor
                    approval.decision_note = request.note
                    approval.version += 1
                    session.add(
                        AuditEvent(
                            id=new_uuid(),
                            event_type="approval.decided",
                            actor=request.actor,
                            entity_type="approval_request",
                            entity_id=approval.id,
                            occurred_at=approval.decided_at,
                            payload_json={
                                "decision": request.decision.value,
                                "risk_type": approval.risk_type,
                                "deal_id": approval.deal_id,
                                "note": request.note,
                            },
                        )
                    )
                row = session.execute(
                    select(ApprovalRequest, CallTranscript, Deal, Company)
                    .join(CallTranscript, CallTranscript.id == ApprovalRequest.source_id)
                    .join(Deal, Deal.id == ApprovalRequest.deal_id)
                    .join(Company, Company.id == ApprovalRequest.company_id)
                    .where(ApprovalRequest.id == approval.id)
                ).one()
                return self._record(*row)

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

    @staticmethod
    def _sync_candidates(session: Session) -> None:
        calls = session.scalars(
            select(CallTranscript).where(
                or_(
                    func.lower(CallTranscript.summary).like("%economic buyer%"),
                    func.lower(CallTranscript.transcript).like("%economic buyer%"),
                )
            )
        ).all()
        for call in calls:
            deal = session.get(Deal, call.deal_id) if call.deal_id else None
            if deal is None:
                deal = session.scalar(
                    select(Deal)
                    .where(Deal.primary_lead_id == call.lead_id)
                    .order_by(Deal.id)
                )
            if deal is None:
                continue
            existing = session.scalar(
                select(ApprovalRequest).where(
                    ApprovalRequest.risk_type == RISK_TYPE,
                    ApprovalRequest.source_id == call.id,
                )
            )
            if existing is None:
                session.add(
                    ApprovalRequest(
                        id=f"risk-{call.id}",
                        risk_type=RISK_TYPE,
                        status=ApprovalStatus.PENDING.value,
                        source_type="call_transcript",
                        source_id=call.id,
                        deal_id=deal.id,
                        company_id=deal.company_id,
                        created_at=_utc(call.occurred_at),
                        version=1,
                    )
                )
        session.flush()

    @staticmethod
    def _record(
        approval: ApprovalRequest,
        call: CallTranscript,
        deal: Deal,
        company: Company,
    ) -> ApprovalRecord:
        return ApprovalRecord(
            id=approval.id,
            risk_type=approval.risk_type,
            status=ApprovalStatus(approval.status),
            deal_id=UUID(deal.id),
            company_id=UUID(company.id),
            company_name=company.name,
            deal_name=deal.name,
            deal_stage=deal.stage,
            amount_minor=deal.amount_minor,
            created_at=_utc(approval.created_at),
            evidence=[
                ApprovalEvidence(
                    source_id=UUID(call.id),
                    source_type="call_transcript",
                    summary=call.summary,
                    occurred_at=_utc(call.occurred_at),
                )
            ],
            decided_at=_utc(approval.decided_at) if approval.decided_at else None,
            decided_by=approval.decided_by,
            decision_note=approval.decision_note,
        )
