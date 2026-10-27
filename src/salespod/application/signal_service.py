from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from salespod.domain.contracts import ListSignalsRequest, SignalEventSummary
from salespod.domain.enums import SignalStatus
from salespod.domain.errors import ConflictError, NotFoundError
from salespod.infrastructure.db.models import AuditEvent, Company, SignalEvent
from salespod.infrastructure.db.repositories import new_uuid


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class SignalService:
    """Transactional reads and acknowledgements for company signal events."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def list_events(self, request: ListSignalsRequest) -> list[SignalEventSummary]:
        with self.session_factory() as session:
            statement = select(SignalEvent, Company).join(
                Company,
                Company.id == SignalEvent.company_id,
            )
            if request.company_id:
                statement = statement.where(SignalEvent.company_id == str(request.company_id))
            if request.event_type:
                statement = statement.where(SignalEvent.event_type == request.event_type.value)
            if request.status:
                statement = statement.where(SignalEvent.status == request.status.value)
            if request.query:
                query = f"%{request.query.lower()}%"
                statement = statement.where(
                    or_(
                        SignalEvent.headline.ilike(query),
                        SignalEvent.summary.ilike(query),
                        Company.name.ilike(query),
                        Company.domain.ilike(query),
                    )
                )
            rows = session.execute(
                statement.order_by(SignalEvent.occurred_at.desc(), SignalEvent.id).limit(
                    request.limit
                )
            ).all()
        return [self._summary(event, company) for event, company in rows]

    def get_event(self, signal_id: UUID | str) -> SignalEventSummary:
        with self.session_factory() as session:
            row = session.execute(
                select(SignalEvent, Company)
                .join(Company, Company.id == SignalEvent.company_id)
                .where(SignalEvent.id == str(signal_id))
            ).one_or_none()
        if row is None:
            raise NotFoundError(f"signal {signal_id} was not found")
        return self._summary(*row)

    def acknowledge(
        self,
        signal_id: UUID | str,
        *,
        actor: str,
        note: str | None = None,
    ) -> SignalEventSummary:
        with self.session_factory() as session:
            with session.begin():
                event = session.get(SignalEvent, str(signal_id))
                if event is None:
                    raise NotFoundError(f"signal {signal_id} was not found")
                if event.status == SignalStatus.DISMISSED.value:
                    raise ConflictError(f"signal {signal_id} has already been dismissed")
                if event.status == SignalStatus.NEW.value:
                    event.status = SignalStatus.ACKNOWLEDGED.value
                    session.add(
                        AuditEvent(
                            id=new_uuid(),
                            event_type="signal.acknowledged",
                            actor=actor,
                            entity_type="signal_event",
                            entity_id=event.id,
                            occurred_at=datetime.now(UTC),
                            payload_json={
                                "company_id": event.company_id,
                                "event_type": event.event_type,
                                "note": note,
                            },
                        )
                    )
                company = session.get(Company, event.company_id)
                if company is None:
                    raise NotFoundError(f"company {event.company_id} was not found")
                session.flush()
                return self._summary(event, company)

    @staticmethod
    def _summary(event: SignalEvent, company: Company) -> SignalEventSummary:
        return SignalEventSummary(
            id=UUID(event.id),
            company_id=UUID(company.id),
            company_name=company.name,
            company_domain=company.domain,
            event_type=event.event_type,
            headline=event.headline,
            summary=event.summary,
            source=event.source,
            source_url=event.source_url,
            occurred_at=_utc(event.occurred_at),
            status=event.status,
            relevance_score=event.relevance_score,
            suggested_action=event.suggested_action,
            payload=event.payload_json or {},
        )
