from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from faker import Faker
from sqlalchemy.orm import Session

from salespod.domain.enums import ActivityType, DealStage, LeadStatus
from salespod.infrastructure.db.models import (
    Activity,
    Base,
    CallTranscript,
    Company,
    Deal,
    DealStageHistory,
    EmailThread,
    Lead,
)
from salespod.infrastructure.db.session import build_engine

SEED_NAMESPACE = UUID("7efc8d77-54c6-4d59-b4be-07c9c4b6f70a")
COMPANY_COUNT = 80
LEAD_COUNT = 500
DEAL_COUNT = 120
EMAIL_COUNT = 1_500
CALL_COUNT = 60


@dataclass(frozen=True)
class SeedResult:
    counts: dict[str, int]
    truth_manifest: dict[str, Any]


def stable_id(kind: str, index: int) -> str:
    return str(uuid5(SEED_NAMESPACE, f"{kind}:{index}"))


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return result or "company"


class SyntheticCrmGenerator:
    """Create a stable, realistic CRM fixture without network dependencies."""

    def __init__(self, *, seed: int = 424242, as_of: datetime) -> None:
        self.seed = seed
        self.as_of = _utc(as_of)
        self.random = random.Random(seed)
        self.fake = Faker("en_US")
        self.fake.seed_instance(seed)

        self.companies: list[Company] = []
        self.leads: list[Lead] = []
        self.deals: list[Deal] = []
        self.emails: list[EmailThread] = []
        self.calls: list[CallTranscript] = []
        self.activities: list[Activity] = []
        self.history: list[DealStageHistory] = []
        self.truth_cases: list[dict[str, Any]] = []

    def generate(self) -> tuple[list[Any], dict[str, Any]]:
        self._companies()
        self._leads()
        self._deals()
        self._emails()
        self._calls()
        self._initial_stage_history()
        self._validate()
        return (
            [
                *self.companies,
                *self.leads,
                *self.deals,
                *self.emails,
                *self.calls,
                *self.activities,
                *self.history,
            ],
            self._manifest(),
        )

    def _timestamp(self, *, days_ago: int, hour: int | None = None) -> datetime:
        chosen_hour = hour if hour is not None else self.random.randint(8, 17)
        return self.as_of - timedelta(
            days=days_ago,
            hours=self.as_of.hour - chosen_hour,
            minutes=self.as_of.minute,
            seconds=self.as_of.second,
        )

    def _companies(self) -> None:
        industries = [
            "Fintech",
            "Healthcare",
            "SaaS",
            "Manufacturing",
            "Retail",
            "Logistics",
            "Cybersecurity",
            "Professional Services",
        ]
        bands = ["11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001+"]
        regions = ["North America", "United Kingdom", "DACH", "Nordics", "ANZ", "Benelux"]
        used_domains: set[str] = set()
        for index in range(COMPANY_COUNT):
            name = self.fake.company().replace(",", "")
            domain = f"{_slug(name)}.example.com"
            while domain in used_domains:
                domain = f"{_slug(name)}-{index}.example.com"
            used_domains.add(domain)
            self.companies.append(
                Company(
                    id=stable_id("company", index),
                    name=name,
                    domain=domain,
                    industry=industries[index % len(industries)],
                    employee_band=bands[(index * 3) % len(bands)],
                    region=regions[(index * 5) % len(regions)],
                )
            )

    def _leads(self) -> None:
        titles = [
            "VP of Revenue",
            "Chief Technology Officer",
            "Director of Sales Operations",
            "Head of Marketing",
            "VP of Customer Success",
            "Finance Director",
            "Procurement Manager",
            "Revenue Operations Manager",
        ]
        owners = ["Avery Chen", "Jordan Patel", "Morgan Brooks", "Riley Singh", "Taylor Kim"]
        sources = ["inbound", "conference", "partner", "outbound", "product-led"]
        statuses = list(LeadStatus)
        for index in range(LEAD_COUNT):
            company = self.companies[index % COMPANY_COUNT]
            first = self.fake.first_name()
            last = self.fake.last_name()
            name = f"{first} {last}"
            email = f"{_slug(first)}.{_slug(last)}{index}@{company.domain}"
            self.leads.append(
                Lead(
                    id=stable_id("lead", index),
                    company_id=company.id,
                    name=name,
                    title=titles[(index * 7) % len(titles)],
                    email=email,
                    status=statuses[(index * 11) % len(statuses)].value,
                    source=sources[(index * 13) % len(sources)],
                    score=45 + ((index * 17) % 56),
                    owner=owners[(index * 3) % len(owners)],
                    created_at=self._timestamp(days_ago=30 + (index % 300)),
                )
            )

    def _deals(self) -> None:
        stages = list(DealStage)
        probabilities = {
            DealStage.DISCOVERY: 0.10,
            DealStage.QUALIFICATION: 0.25,
            DealStage.PROPOSAL: 0.45,
            DealStage.NEGOTIATION: 0.65,
            DealStage.CLOSED_WON: 1.0,
            DealStage.CLOSED_LOST: 0.0,
        }
        owners = ["Avery Chen", "Jordan Patel", "Morgan Brooks", "Riley Singh", "Taylor Kim"]
        for index in range(DEAL_COUNT):
            company = self.companies[(index * 7) % COMPANY_COUNT]
            lead = next(item for item in self.leads if item.company_id == company.id)
            if index < 5:
                stage = DealStage.NEGOTIATION
                days_in_stage = 28 + index * 4
            else:
                stage = stages[(index * 5 + 1) % len(stages)]
                days_in_stage = 3 + ((index * 9) % 35)
            stage_entered = self._timestamp(days_ago=days_in_stage)
            created_at = stage_entered - timedelta(days=8 + (index * 3) % 65)
            amount = (18_000 + ((index * 7_331) % 182_000)) * 100
            self.deals.append(
                Deal(
                    id=stable_id("deal", index),
                    company_id=company.id,
                    primary_lead_id=lead.id,
                    name=f"{company.name} Revenue Platform",
                    stage=stage.value,
                    amount_minor=amount,
                    currency="USD",
                    close_date=self.as_of + timedelta(days=15 + ((index * 11) % 120)),
                    probability=probabilities[stage],
                    owner=owners[(index * 3) % len(owners)],
                    created_at=created_at,
                    stage_entered_at=stage_entered,
                    version=1,
                )
            )

    def _emails(self) -> None:
        reply_statuses = ["replied", "ghosted", "objection", "meeting_booked", "no_response"]
        objections = [
            "The team is comparing options and needs a clearer implementation plan.",
            "The budget is under review and the buyer asked for a business case.",
            "The prospect wants proof from a similar company before progressing.",
            "The security review is the main blocker for the next step.",
        ]
        for index in range(EMAIL_COUNT):
            lead = self.leads[(index * 17) % LEAD_COUNT]
            started = self._timestamp(days_ago=10 + ((index * 19) % 330))
            last = started + timedelta(days=index % 12, hours=index % 7)
            status = reply_statuses[(index * 7) % len(reply_statuses)]
            message_count = 1 if status in {"ghosted", "no_response"} else 2 + index % 4
            summary = (
                "Prospect replied positively and requested a working session."
                if status == "meeting_booked"
                else objections[index % len(objections)]
                if status == "objection"
                else "Initial personalized outreach covering the prospect's growth priorities."
            )
            body = (
                f"Hi {lead.name.split()[0]},\n\n"
                f"Based on {lead.title.lower()} priorities at your company, here is a concise "
                "way to improve pipeline visibility and rep productivity.\n\n"
                f"{summary}\n\nBest,\nSales Pod"
            )
            self.emails.append(
                EmailThread(
                    id=stable_id("email", index),
                    company_id=lead.company_id,
                    lead_id=lead.id,
                    subject=f"A revenue workflow for {lead.title}",
                    summary=summary,
                    body=body,
                    reply_status=status,
                    message_count=message_count,
                    started_at=started,
                    last_message_at=last,
                )
            )

    def _calls(self) -> None:
        competitor_names = ["Northstar", "PipelinePro", "RevPilot", "QuotaWorks"]
        for index in range(CALL_COUNT):
            deal = self.deals[index % DEAL_COUNT]
            lead = next(item for item in self.leads if item.id == deal.primary_lead_id)
            occurred_at = self._timestamp(days_ago=4 + ((index * 13) % 160))
            if index < 5:
                competitor = competitor_names[index % len(competitor_names)]
                transcript = (
                    f"AE: Thanks for joining, {lead.name}. What would need to happen next?\n"
                    f"Buyer: We are also looking at {competitor}. I still need to bring our CFO "
                    "into this, and the budget may be frozen until Q1.\n"
                    "AE: Understood. Who owns the final approval?\n"
                    "Buyer: I am not sure yet; finance has not assigned an economic buyer."
                )
                summary = (
                    "Competitor mentioned; economic buyer is not identified and budget timing "
                    "is uncertain."
                )
                next_steps = (
                    "Confirm economic buyer, budget owner, and decision process before "
                    "forecast commitment."
                )
                self.truth_cases.append(
                    {
                        "deal_id": deal.id,
                        "company_id": deal.company_id,
                        "reason": "missing_economic_buyer",
                        "expected_stage": DealStage.NEGOTIATION.value,
                        "evidence": {
                            "call_id": stable_id("call", index),
                            "phrases": ["bring our CFO", "budget may be frozen", "economic buyer"],
                        },
                    }
                )
            else:
                transcript = (
                    f"AE: How is the current workflow performing, {lead.name}?\n"
                    "Buyer: The team likes the direction. We need to align stakeholders "
                    "on timing.\n"
                    "AE: I will send a recap and proposed next steps."
                )
                summary = "Discovery call covered workflow priorities and timing."
                next_steps = "Send recap and schedule the next stakeholder meeting."
            self.calls.append(
                CallTranscript(
                    id=stable_id("call", index),
                    company_id=deal.company_id,
                    lead_id=lead.id,
                    deal_id=deal.id,
                    summary=summary,
                    transcript=transcript,
                    occurred_at=occurred_at,
                    next_steps=next_steps,
                )
            )
            self.activities.append(
                Activity(
                    id=stable_id("call-activity", index),
                    company_id=deal.company_id,
                    lead_id=lead.id,
                    deal_id=deal.id,
                    activity_type=ActivityType.CALL.value,
                    body=summary,
                    occurred_at=occurred_at,
                    actor="Sales Pod",
                    idempotency_key=f"seed-call-{index}",
                    metadata_json={"transcript_id": stable_id("call", index)},
                )
            )

    def _initial_stage_history(self) -> None:
        for index, deal in enumerate(self.deals):
            self.history.append(
                DealStageHistory(
                    id=stable_id("stage-history", index),
                    deal_id=deal.id,
                    from_stage=None,
                    to_stage=deal.stage,
                    reason="Initial synthetic CRM state",
                    actor="seed",
                    occurred_at=deal.stage_entered_at,
                )
            )

    def _validate(self) -> None:
        assert len(self.companies) == COMPANY_COUNT
        assert len(self.leads) == LEAD_COUNT
        assert len(self.deals) == DEAL_COUNT
        assert len(self.emails) == EMAIL_COUNT
        assert len(self.calls) == CALL_COUNT
        assert len(self.truth_cases) == 5
        assert len({company.domain for company in self.companies}) == COMPANY_COUNT
        assert len({lead.email for lead in self.leads}) == LEAD_COUNT
        company_ids = {company.id for company in self.companies}
        lead_ids = {lead.id for lead in self.leads}
        for lead in self.leads:
            assert lead.company_id in company_ids
        for deal in self.deals:
            assert deal.company_id in company_ids
            assert deal.primary_lead_id in lead_ids
            assert deal.created_at <= deal.stage_entered_at <= deal.close_date

    def _manifest(self) -> dict[str, Any]:
        stage_totals: dict[str, dict[str, int]] = {}
        for deal in self.deals:
            row = stage_totals.setdefault(deal.stage, {"count": 0, "amount_minor": 0})
            row["count"] += 1
            row["amount_minor"] += deal.amount_minor
        expected_pipeline = {
            "currency": "USD",
            "stages": stage_totals,
            "total_count": len(self.deals),
            "total_amount_minor": sum(deal.amount_minor for deal in self.deals),
        }
        manifest: dict[str, Any] = {
            "manifest_version": 1,
            "seed": self.seed,
            "as_of": self.as_of.isoformat(),
            "counts": {
                "companies": len(self.companies),
                "leads": len(self.leads),
                "deals": len(self.deals),
                "email_threads": len(self.emails),
                "call_transcripts": len(self.calls),
                "activities": len(self.activities),
                "stage_history": len(self.history),
            },
            "ground_truth_cases": self.truth_cases,
            "expected_pipeline": expected_pipeline,
        }
        canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        manifest["content_hash"] = hashlib.sha256(canonical).hexdigest()
        return manifest


def seed_database(
    database_url: str,
    *,
    seed: int = 424242,
    as_of: datetime,
    reset: bool = False,
    truth_output: str | Path | None = None,
) -> SeedResult:
    """Seed a database and optionally write the evaluation manifest."""
    engine = build_engine(database_url)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    records, manifest = SyntheticCrmGenerator(seed=seed, as_of=as_of).generate()
    with Session(engine) as session:
        # Insert in dependency order. These are intentionally explicit rather
        # than relying on ORM relationships, because the fixture generator
        # keeps entities detached and transport-independent.
        for model in (
            Company,
            Lead,
            Deal,
            EmailThread,
            CallTranscript,
            Activity,
            DealStageHistory,
        ):
            session.add_all(record for record in records if isinstance(record, model))
            session.flush()
        session.commit()
    if truth_output:
        output = Path(truth_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return SeedResult(counts=manifest["counts"], truth_manifest=manifest)
