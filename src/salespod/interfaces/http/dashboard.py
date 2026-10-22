from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from salespod.domain.contracts import ActivitySummary
from salespod.domain.enums import ActivityType
from salespod.infrastructure.db.models import Activity


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class DashboardRepository:
    """Read-only dashboard queries that complement the CRM application service."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def recent_activities(self, *, limit: int = 10) -> list[ActivitySummary]:
        with self.session_factory() as session:
            activities = session.scalars(
                select(Activity)
                .order_by(Activity.occurred_at.desc(), Activity.id)
                .limit(limit)
            ).all()
        return [self._summary(activity) for activity in activities]

    @staticmethod
    def _summary(activity: Activity) -> ActivitySummary:
        return ActivitySummary(
            id=UUID(activity.id),
            activity_type=ActivityType(activity.activity_type),
            body=activity.body,
            actor=activity.actor,
            occurred_at=_utc(activity.occurred_at),
            company_id=UUID(activity.company_id) if activity.company_id else None,
            lead_id=UUID(activity.lead_id) if activity.lead_id else None,
            deal_id=UUID(activity.deal_id) if activity.deal_id else None,
            metadata=activity.metadata_json or {},
        )
