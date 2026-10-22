from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Activity, Company, Deal, Lead


def now_utc() -> datetime:
    return datetime.now(UTC)


def uuid_text(value: UUID | str) -> str:
    return str(value)


def new_uuid() -> str:
    return str(uuid4())


def get_one(session: Session, model: type[Any], value: UUID | str) -> Any | None:
    return session.get(model, uuid_text(value))


def require_one(session: Session, model: type[Any], value: UUID | str) -> Any:
    return session.get(model, uuid_text(value))


def select_company(session: Session, company_id: str) -> Company | None:
    return session.scalar(select(Company).where(Company.id == company_id))


def select_lead(session: Session, lead_id: str) -> Lead | None:
    return session.scalar(select(Lead).where(Lead.id == lead_id))


def select_deal(session: Session, deal_id: str) -> Deal | None:
    return session.scalar(select(Deal).where(Deal.id == deal_id))


def add_activity(
    session: Session,
    *,
    activity_type: str,
    body: str,
    actor: str,
    occurred_at: datetime,
    company_id: str | None,
    lead_id: str | None,
    deal_id: str | None,
    idempotency_key: str | None,
    metadata: dict[str, Any],
) -> Activity:
    activity = Activity(
        id=new_uuid(),
        activity_type=activity_type,
        body=body,
        actor=actor,
        occurred_at=occurred_at,
        company_id=company_id,
        lead_id=lead_id,
        deal_id=deal_id,
        idempotency_key=idempotency_key,
        metadata_json=metadata,
    )
    session.add(activity)
    return activity
