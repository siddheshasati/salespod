from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from salespod.infrastructure.db.models import AuditEvent

from .schemas import AuditEventSummary


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AuditRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def list(self, *, limit: int = 50) -> list[AuditEventSummary]:
        with self.session_factory() as session:
            events = session.scalars(
                select(AuditEvent)
                .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id)
                .limit(limit)
            ).all()
        return [self._summary(event) for event in events]

    @staticmethod
    def _summary(event: AuditEvent) -> AuditEventSummary:
        return AuditEventSummary(
            id=UUID(event.id),
            event_type=event.event_type,
            actor=event.actor,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            occurred_at=_utc(event.occurred_at),
            payload=event.payload_json or {},
        )
