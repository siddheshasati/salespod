from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from salespod.domain.enums import SignalEventType, SignalStatus
from salespod.infrastructure.db.models import AuditEvent, Company, Deal, SignalEvent
from salespod.infrastructure.db.repositories import new_uuid

SIMULATED_TEMPLATES: dict[str, dict[str, Any]] = {
    "funding_round": {
        "event_type": SignalEventType.FUNDING_ROUND.value,
        "headline_template": "{company}: Announces ${amount}M {round} to scale GTM",
        "summary_template": (
            "{company} secured a ${amount}M {round} round led by {lead_investor}. "
            "The infusion signals accelerated budget allocation for modern revenue workflow "
            "automation, pipeline governance, and sales predictability."
        ),
        "source": "TechCrunch Funding Wire",
        "source_url_pattern": "https://techcrunch.example.com/{domain}/funding-announcement",
        "relevance_score": 96,
        "suggested_action": (
            "Trigger account research, prioritize executive buyers, and launch a "
            "funding-tailored outreach variant."
        ),
        "default_payload": {
            "round": "Series B",
            "amount_minor": 45_000_000,
            "lead_investor": "Bessemer Venture Partners",
            "valuation_minor": 225_000_000,
            "strategic_initiatives": [
                "Revenue stack overhaul",
                "Sales team expansion",
                "Predictive forecasting",
            ],
        },
    },
    "new_cto": {
        "event_type": SignalEventType.NEW_CTO.value,
        "headline_template": "{company}: Appoints Dr. {executive_name} as Chief Technology Officer",
        "summary_template": (
            "{company} has named Dr. {executive_name} (formerly of {prior_company}) as Chief "
            "Technology Officer. The transition signals an imminent review of technical "
            "integrations, data security standards, and sales stack consolidation."
        ),
        "source": "Executive Talent Monitor",
        "source_url_pattern": "https://talentintel.example.com/{domain}/new-cto-appointment",
        "relevance_score": 98,
        "suggested_action": (
            "Engage the technical buying committee with a low-friction architecture and "
            "integration validation angle."
        ),
        "default_payload": {
            "executive_name": "Elena Rostova",
            "title": "Chief Technology Officer",
            "prior_company": "Snowflake",
            "focus_areas": [
                "Cloud architecture",
                "Security compliance",
                "API-first data integrations",
            ],
        },
    },
    "layoffs": {
        "event_type": SignalEventType.LAYOFFS.value,
        "headline_template": (
            "{company}: Restructuring plan announced to drive unit economics and efficiency"
        ),
        "summary_template": (
            "{company} announced an organizational restructuring affecting {pct}% of workforce "
            "to improve operating margins. Department heads are tasked with consolidating "
            "redundant software vendors and automating manual revenue tasks."
        ),
        "source": "Market Intel Brief",
        "source_url_pattern": "https://marketbrief.example.com/{domain}/workforce-restructure",
        "relevance_score": 88,
        "suggested_action": (
            "Present an efficiency and cost-consolidation business case focused on rep "
            "productivity without head-count addition."
        ),
        "default_payload": {
            "pct": 12,
            "departments_affected": ["Recruiting", "Mid-market sales", "General support"],
            "mandate": "Vendor consolidation and automated pipeline coverage",
        },
    },
    "tech_stack": {
        "event_type": SignalEventType.TECH_STACK_CHANGE.value,
        "headline_template": (
            "{company}: Detected pilot evaluation of next-generation revenue intelligence"
        ),
        "summary_template": (
            "Telemetry signals detect {company} testing API connectors for next-gen revenue "
            "platforms while phasing out legacy conversation recording tools. Signals an active "
            "buying window for unified pipeline control."
        ),
        "source": "Technographics Telemetry",
        "source_url_pattern": "https://techradar.example.com/{domain}/stack-detection",
        "relevance_score": 94,
        "suggested_action": (
            "Position direct Salesforce interoperability and highlight automated deal risk "
            "detection."
        ),
        "default_payload": {
            "category": "revenue_intelligence",
            "detected_pilot": "Agentic Sales Pods",
            "phasing_out": "Legacy standalone call recorder",
            "integration_requirements": ["Salesforce CRM", "Slack Alerts", "FastMCP standard"],
        },
    },
    "leadership_change": {
        "event_type": SignalEventType.LEADERSHIP_CHANGE.value,
        "headline_template": "{company}: Welcomes {executive_name} as Chief Revenue Officer",
        "summary_template": (
            "{company} brought on {executive_name} as CRO to unify sales, customer success, "
            "and revenue operations. New CROs routinely reset forecasting methodologies and "
            "demand higher pipeline visibility."
        ),
        "source": "Company Press Release",
        "source_url_pattern": "https://news.example.com/{domain}/cro-announcement",
        "relevance_score": 95,
        "suggested_action": (
            "Reach out to the new CRO with an executive peer benchmark and immediate "
            "pipeline blind-spot audit."
        ),
        "default_payload": {
            "executive_name": "Marcus Sterling",
            "title": "Chief Revenue Officer",
            "prior_company": "Datadog",
            "priorities": ["Q4 commit accuracy", "Economic buyer verification", "Rep ramp time"],
        },
    },
}


class SignalStreamService:
    """Manages simulated event stream generation and emission."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def simulate_event(
        self,
        event_type: str | None = None,
        company_id: str | None = None,
        actor: str = "signal_monitor",
    ) -> SignalEvent:
        """Create and persist a realistic simulated signal event."""
        # Normalize event_type
        type_key = (event_type or "").lower().strip()
        if type_key in ("tech_stack", "tech-stack", "tech_stack_change"):
            type_key = "tech_stack"
        elif type_key in ("new_cto", "cto"):
            type_key = "new_cto"
        elif type_key in ("leadership", "leadership_change", "executive_change"):
            type_key = "leadership_change"
        elif type_key in ("funding", "funding_round"):
            type_key = "funding_round"
        elif type_key in ("layoffs", "layoff"):
            type_key = "layoffs"
        else:
            type_key = random.choice(list(SIMULATED_TEMPLATES.keys()))

        template = SIMULATED_TEMPLATES[type_key]

        # Select company
        company = None
        if company_id:
            try:
                company = self.session.get(Company, str(UUID(company_id)))
            except ValueError:
                pass

        if company is None:
            # Pick a company that has deals
            deals = self.session.scalars(
                select(Deal).order_by(Deal.amount_minor.desc()).limit(15)
            ).all()
            if deals:
                chosen_deal = random.choice(deals)
                company = self.session.get(Company, chosen_deal.company_id)
            if company is None:
                company = self.session.scalars(select(Company).limit(1)).first()
            if company is None:
                raise RuntimeError(
                    "No company available in the database to associate with signal event."
                )

        now = datetime.now(UTC)
        payload = dict(template["default_payload"])
        headline = template["headline_template"].format(
            company=company.name,
            amount=payload.get("amount_minor", 40_000_000) // 1_000_000,
            round=payload.get("round", "Series B"),
            executive_name=payload.get("executive_name", "Alex Rivera"),
            prior_company=payload.get("prior_company", "CloudCorp"),
            pct=payload.get("pct", 10),
        )
        summary = template["summary_template"].format(
            company=company.name,
            domain=company.domain,
            amount=payload.get("amount_minor", 40_000_000) // 1_000_000,
            round=payload.get("round", "Series B"),
            lead_investor=payload.get("lead_investor", "Benchmark Capital"),
            executive_name=payload.get("executive_name", "Alex Rivera"),
            prior_company=payload.get("prior_company", "CloudCorp"),
            pct=payload.get("pct", 10),
        )
        source_url = template["source_url_pattern"].format(domain=company.domain)

        signal = SignalEvent(
            id=new_uuid(),
            company_id=company.id,
            event_type=template["event_type"],
            headline=headline,
            summary=summary,
            source=template["source"],
            source_url=source_url,
            occurred_at=now,
            status=SignalStatus.NEW.value,
            relevance_score=template["relevance_score"],
            suggested_action=template["suggested_action"],
            payload_json={
                **payload,
                "simulated": True,
                "domain": company.domain,
                "company_name": company.name,
            },
            created_at=now,
        )
        self.session.add(signal)

        # Audit event for the emitted signal
        self.session.add(
            AuditEvent(
                id=new_uuid(),
                event_type="signal.stream_emitted",
                actor=actor,
                entity_type="signal_event",
                entity_id=signal.id,
                occurred_at=now,
                payload_json={
                    "event_type": signal.event_type,
                    "company_id": company.id,
                    "company_name": company.name,
                    "headline": signal.headline,
                    "relevance_score": signal.relevance_score,
                },
            )
        )
        self.session.flush()
        return signal

    def seed_stream_cohort(self) -> list[SignalEvent]:
        """Seed all 5 core simulated signal event scenarios across active accounts."""
        event_keys = ["funding_round", "new_cto", "layoffs", "tech_stack", "leadership_change"]
        companies = self.session.scalars(select(Company).order_by(Company.name).limit(10)).all()
        created: list[SignalEvent] = []

        for idx, key in enumerate(event_keys):
            company = companies[idx % len(companies)] if companies else None
            sig = self.simulate_event(event_type=key, company_id=company.id if company else None)
            created.append(sig)

        return created
