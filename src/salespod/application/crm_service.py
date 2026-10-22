from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from salespod.domain.contracts import (
    ActivitySummary,
    CompanySummary,
    DealDetail,
    GetDealResponse,
    LeadSummary,
    LogActivityRequest,
    LogActivityResponse,
    PipelineSnapshotResponse,
    PipelineStageSummary,
    SearchLeadsRequest,
    SearchLeadsResponse,
    StageChange,
    UpdateStageRequest,
    UpdateStageResponse,
)
from salespod.domain.enums import ActivityType, DealStage, LeadStatus
from salespod.domain.errors import ConflictError, NotFoundError, ValidationError
from salespod.infrastructure.db.models import Activity, Company, Deal, DealStageHistory, Lead
from salespod.infrastructure.db.repositories import new_uuid, now_utc

_STAGE_ORDER = list(DealStage)
_PROBABILITY = {
    DealStage.DISCOVERY: 0.10,
    DealStage.QUALIFICATION: 0.25,
    DealStage.PROPOSAL: 0.45,
    DealStage.NEGOTIATION: 0.65,
    DealStage.CLOSED_WON: 1.0,
    DealStage.CLOSED_LOST: 0.0,
}
_ALLOWED_TRANSITIONS = {
    DealStage.DISCOVERY: {DealStage.QUALIFICATION, DealStage.CLOSED_LOST},
    DealStage.QUALIFICATION: {DealStage.PROPOSAL, DealStage.CLOSED_LOST},
    DealStage.PROPOSAL: {DealStage.NEGOTIATION, DealStage.CLOSED_LOST},
    DealStage.NEGOTIATION: {DealStage.CLOSED_WON, DealStage.CLOSED_LOST},
    DealStage.CLOSED_WON: set(),
    DealStage.CLOSED_LOST: set(),
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        value = int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, UnicodeDecodeError, base64.binascii.Error) as exc:
        raise ValidationError("cursor must be a valid pagination cursor") from exc
    if value < 0:
        raise ValidationError("cursor cannot be negative")
    return value


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


class CrmService:
    """Transactional CRM use cases shared by MCP and agents."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def search_leads(self, request: SearchLeadsRequest) -> SearchLeadsResponse:
        offset = _decode_cursor(request.cursor)
        with self.session_factory() as session:
            statement = self._lead_query(request)
            total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
            leads = session.scalars(
                statement.order_by(Lead.id).offset(offset).limit(request.limit)
            ).all()
            items = [self._lead_summary(session, lead) for lead in leads]
        next_cursor = (
            _encode_cursor(offset + request.limit) if offset + len(items) < total else None
        )
        return SearchLeadsResponse(items=items, next_cursor=next_cursor, total_estimate=total)

    def get_deal(self, deal_id: UUID | str) -> GetDealResponse:
        with self.session_factory() as session:
            deal = session.get(Deal, str(deal_id))
            if deal is None:
                raise NotFoundError(f"deal {deal_id} was not found")
            company = session.get(Company, deal.company_id)
            if company is None:
                raise NotFoundError(f"company {deal.company_id} was not found")
            lead = session.get(Lead, deal.primary_lead_id) if deal.primary_lead_id else None
            activities = session.scalars(
                select(Activity)
                .where(Activity.deal_id == deal.id)
                .order_by(Activity.occurred_at.desc())
                .limit(20)
            ).all()
            history = session.scalars(
                select(DealStageHistory)
                .where(DealStageHistory.deal_id == deal.id)
                .order_by(DealStageHistory.occurred_at.asc())
            ).all()
            return GetDealResponse(
                deal=self._deal_detail(deal),
                company=self._company_summary(company),
                primary_lead=self._lead_summary(session, lead) if lead else None,
                recent_activities=[self._activity_summary(item) for item in activities],
                stage_history=[self._stage_change(item) for item in history],
            )

    def update_stage(self, request: UpdateStageRequest) -> UpdateStageResponse:
        with self.session_factory() as session:
            with session.begin():
                if request.idempotency_key:
                    replay = session.scalar(
                        select(Activity).where(Activity.idempotency_key == request.idempotency_key)
                    )
                    if replay is not None:
                        history_id = replay.metadata_json.get("stage_history_id")
                        history = session.get(DealStageHistory, history_id) if history_id else None
                        deal = session.get(Deal, str(request.deal_id))
                        if deal is None or history is None:
                            raise ConflictError("idempotency record is missing its stage change")
                        return UpdateStageResponse(
                            deal=self._deal_detail(deal), stage_change=self._stage_change(history)
                        )
                deal = session.get(Deal, str(request.deal_id))
                if deal is None:
                    raise NotFoundError(f"deal {request.deal_id} was not found")
                current_stage = DealStage(deal.stage)
                if deal.version != request.expected_version:
                    raise ConflictError(
                        f"deal version is {deal.version}; expected {request.expected_version}"
                    )
                if request.new_stage == current_stage:
                    raise ValidationError("new stage must differ from the current stage")
                if request.new_stage not in _ALLOWED_TRANSITIONS[current_stage]:
                    raise ValidationError(
                        f"cannot move a deal from {current_stage.value} "
                        f"to {request.new_stage.value}"
                    )
                occurred_at = now_utc()
                history = DealStageHistory(
                    id=new_uuid(),
                    deal_id=deal.id,
                    from_stage=current_stage.value,
                    to_stage=request.new_stage.value,
                    reason=request.reason,
                    actor=request.actor,
                    occurred_at=occurred_at,
                )
                deal.stage = request.new_stage.value
                deal.probability = _PROBABILITY[request.new_stage]
                deal.stage_entered_at = occurred_at
                deal.version += 1
                session.add(history)
                if request.idempotency_key:
                    session.add(
                        Activity(
                            id=new_uuid(),
                            company_id=deal.company_id,
                            lead_id=deal.primary_lead_id,
                            deal_id=deal.id,
                            activity_type=ActivityType.STAGE_CHANGE.value,
                            body=request.reason,
                            occurred_at=occurred_at,
                            actor=request.actor,
                            idempotency_key=request.idempotency_key,
                            metadata_json={"stage_history_id": history.id},
                        )
                    )
                session.flush()
                return UpdateStageResponse(
                    deal=self._deal_detail(deal), stage_change=self._stage_change(history)
                )

    def log_activity(self, request: LogActivityRequest) -> LogActivityResponse:
        if not any((request.company_id, request.lead_id, request.deal_id)):
            raise ValidationError("an activity must reference a company, lead, or deal")
        occurred_at = _utc(request.occurred_at) if request.occurred_at else now_utc()
        with self.session_factory() as session:
            with session.begin():
                if request.idempotency_key:
                    existing = session.scalar(
                        select(Activity).where(Activity.idempotency_key == request.idempotency_key)
                    )
                    if existing is not None:
                        return LogActivityResponse(activity=self._activity_summary(existing))
                company_id = str(request.company_id) if request.company_id else None
                lead_id = str(request.lead_id) if request.lead_id else None
                deal_id = str(request.deal_id) if request.deal_id else None
                if company_id and session.get(Company, company_id) is None:
                    raise NotFoundError(f"company {company_id} was not found")
                if lead_id and session.get(Lead, lead_id) is None:
                    raise NotFoundError(f"lead {lead_id} was not found")
                if deal_id and session.get(Deal, deal_id) is None:
                    raise NotFoundError(f"deal {deal_id} was not found")
                activity = Activity(
                    id=new_uuid(),
                    company_id=company_id,
                    lead_id=lead_id,
                    deal_id=deal_id,
                    activity_type=request.activity_type.value,
                    body=request.body,
                    actor=request.actor,
                    occurred_at=occurred_at,
                    idempotency_key=request.idempotency_key,
                    metadata_json=request.metadata,
                )
                session.add(activity)
                session.flush()
                return LogActivityResponse(activity=self._activity_summary(activity))

    def get_pipeline_snapshot(
        self,
        *,
        company_id: UUID | str | None = None,
        owner: str | None = None,
        as_of: datetime | None = None,
    ) -> PipelineSnapshotResponse:
        with self.session_factory() as session:
            statement = select(Deal)
            if company_id:
                statement = statement.where(Deal.company_id == str(company_id))
            if owner:
                statement = statement.where(Deal.owner == owner)
            if as_of:
                statement = statement.where(Deal.created_at <= _utc(as_of))
            deals = session.scalars(statement).all()
        rows: list[PipelineStageSummary] = []
        for stage in _STAGE_ORDER:
            stage_deals = [deal for deal in deals if deal.stage == stage.value]
            amount = sum(deal.amount_minor for deal in stage_deals)
            weighted = sum(round(deal.amount_minor * deal.probability) for deal in stage_deals)
            rows.append(
                PipelineStageSummary(
                    stage=stage,
                    count=len(stage_deals),
                    amount_minor=amount,
                    weighted_amount_minor=weighted,
                )
            )
        currency = next((deal.currency for deal in deals), "USD")
        return PipelineSnapshotResponse(
            generated_at=now_utc(),
            currency=currency,
            stages=rows,
            total_count=len(deals),
            total_amount_minor=sum(deal.amount_minor for deal in deals),
            weighted_amount_minor=sum(
                round(deal.amount_minor * deal.probability) for deal in deals
            ),
        )

    @staticmethod
    def _lead_query(request: SearchLeadsRequest) -> Select[Any]:
        statement = select(Lead)
        if request.company_id:
            statement = statement.where(Lead.company_id == str(request.company_id))
        if request.status:
            statement = statement.where(Lead.status == request.status.value)
        if request.query:
            pattern = f"%{request.query.lower()}%"
            statement = statement.join(Company, Company.id == Lead.company_id).where(
                or_(
                    func.lower(Lead.name).like(pattern),
                    func.lower(Lead.email).like(pattern),
                    func.lower(Lead.title).like(pattern),
                    func.lower(Company.name).like(pattern),
                )
            )
        return statement

    @staticmethod
    def _company_summary(company: Company) -> CompanySummary:
        return CompanySummary(
            id=UUID(company.id),
            name=company.name,
            domain=company.domain,
            industry=company.industry,
            employee_band=company.employee_band,
            region=company.region,
        )

    def _lead_summary(self, session: Session, lead: Lead | None) -> LeadSummary:
        if lead is None:
            raise NotFoundError("lead was not found")
        company = session.get(Company, lead.company_id)
        if company is None:
            raise NotFoundError(f"company {lead.company_id} was not found")
        return LeadSummary(
            id=UUID(lead.id),
            company_id=UUID(lead.company_id),
            company_name=company.name,
            name=lead.name,
            title=lead.title,
            email=lead.email,
            status=LeadStatus(lead.status),
            score=lead.score,
            owner=lead.owner,
        )

    @staticmethod
    def _deal_detail(deal: Deal) -> DealDetail:
        return DealDetail(
            id=UUID(deal.id),
            company_id=UUID(deal.company_id),
            primary_lead_id=UUID(deal.primary_lead_id) if deal.primary_lead_id else None,
            name=deal.name,
            stage=DealStage(deal.stage),
            amount_minor=deal.amount_minor,
            currency=deal.currency,
            close_date=_utc(deal.close_date),
            probability=deal.probability,
            owner=deal.owner,
            version=deal.version,
        )

    @staticmethod
    def _activity_summary(activity: Activity) -> ActivitySummary:
        return ActivitySummary(
            id=UUID(activity.id),
            activity_type=ActivityType(activity.activity_type),
            body=activity.body,
            actor=activity.actor,
            occurred_at=_utc(activity.occurred_at),
            company_id=UUID(activity.company_id) if activity.company_id else None,
            lead_id=UUID(activity.lead_id) if activity.lead_id else None,
            deal_id=UUID(activity.deal_id) if activity.deal_id else None,
            metadata=activity.metadata_json,
        )

    @staticmethod
    def _stage_change(history: DealStageHistory) -> StageChange:
        return StageChange(
            id=UUID(history.id),
            deal_id=UUID(history.deal_id),
            from_stage=DealStage(history.from_stage) if history.from_stage else None,
            to_stage=DealStage(history.to_stage),
            reason=history.reason,
            actor=history.actor,
            occurred_at=_utc(history.occurred_at),
        )
