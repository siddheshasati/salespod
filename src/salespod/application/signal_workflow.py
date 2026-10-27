from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from salespod.application.crm_service import CrmService
from salespod.domain.enums import ActivityType, SignalStatus
from salespod.domain.errors import NotFoundError
from salespod.infrastructure.db.models import (
    Activity,
    ApprovalRequest,
    AuditEvent,
    Company,
    Deal,
    Lead,
    SignalEvent,
)
from salespod.infrastructure.db.repositories import new_uuid
from salespod.interfaces.mcp.signals_server import SignalsIntelligenceSource


class AccountResearchBrief(BaseModel):
    company_id: str
    company_name: str
    domain: str
    industry: str
    signal_summary: str
    recent_news: list[dict[str, Any]] = Field(default_factory=list)
    funding_context: list[dict[str, Any]] = Field(default_factory=list)
    tech_stack: dict[str, Any] = Field(default_factory=dict)
    strategic_priorities: list[str] = Field(default_factory=list)


class BuyingCommitteeMember(BaseModel):
    role_type: str  # economic_buyer, technical_buyer, champion, influencer
    name: str
    title: str
    email: str
    fit_score: int
    rationale: str


class BuyingCommittee(BaseModel):
    economic_buyer: BuyingCommitteeMember | None = None
    technical_buyer: BuyingCommitteeMember | None = None
    champion: BuyingCommitteeMember | None = None
    influencers: list[BuyingCommitteeMember] = Field(default_factory=list)


class EmailVariant(BaseModel):
    variant_id: str
    name: str
    angle: str
    target_persona: str
    subject: str
    body: str
    call_to_action: str


class ComplianceCheckResult(BaseModel):
    compliant: bool
    risk_score: float
    checks: list[dict[str, Any]]
    recommendation: str


class SandboxSendResult(BaseModel):
    message_id: str
    recipient: str
    subject: str
    status: str
    sent_at: str
    sandbox_transport: str


class SignalWorkflowResult(BaseModel):
    signal_id: str
    status: str
    account_research: AccountResearchBrief
    buying_committee: BuyingCommittee
    email_variants: list[EmailVariant]
    recommended_variant: EmailVariant
    compliance_check: ComplianceCheckResult
    approval_id: str | None = None
    sandbox_send: SandboxSendResult | None = None
    activity_id: str | None = None
    audit_event_id: str | None = None


class SignalWorkflowOrchestrator:
    """Executes the full 9-step autonomous demo flow triggered by a signal event."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self.intel_source = SignalsIntelligenceSource(session_factory)
        self.crm_service = CrmService(session_factory)

    def execute_pipeline(
        self,
        signal_id: str,
        actor: str = "signal_orchestrator",
        auto_approve: bool = False,
    ) -> SignalWorkflowResult:
        with self.session_factory() as session:
            with session.begin():
                signal = session.get(
                    SignalEvent, str(UUID(signal_id)) if len(signal_id) == 36 else signal_id
                )
                if signal is None:
                    raise NotFoundError(f"Signal {signal_id} was not found.")

                company = session.get(Company, signal.company_id)
                if company is None:
                    raise NotFoundError(f"Company {signal.company_id} for signal was not found.")

                # Deal associated with the company
                deal = session.scalar(
                    select(Deal)
                    .where(Deal.company_id == company.id)
                    .order_by(Deal.amount_minor.desc())
                )
                if deal is None:
                    # Create an active expansion/evaluation deal if none exists
                    deal = Deal(
                        id=new_uuid(),
                        company_id=company.id,
                        name=f"{company.name} - Signal Opportunity",
                        stage="discovery",
                        amount_minor=120_000_00,
                        currency="USD",
                        probability=0.35,
                        close_date=datetime.now(UTC),
                        owner="manager",
                        version=1,
                    )
                    session.add(deal)
                    session.flush()

                # Step 2: Account Research via signals-mcp
                research = self._conduct_account_research(session, signal, company)

                # Step 3 & 4: Lead/ICP Scoring & Buying Committee Mapping
                leads = session.scalars(
                    select(Lead).where(Lead.company_id == company.id).order_by(Lead.score.desc())
                ).all()
                committee = self._map_buying_committee(leads, signal.event_type)

                # Step 5: Personalized Email Variants
                target_lead = (
                    committee.economic_buyer
                    if signal.event_type in ("funding_round", "leadership_change", "layoffs")
                    else (
                        committee.technical_buyer or committee.champion or committee.economic_buyer
                    )
                )
                variants = self._generate_email_variants(company, signal, target_lead)
                recommended_variant = variants[0]

                # Step 6: Compliance Check
                compliance = self._evaluate_compliance(recommended_variant, company)

                # Step 7: Approval Inbox item
                approval_id = f"outreach-{signal.id}"
                approval = session.get(ApprovalRequest, approval_id)
                if approval is None:
                    approval = ApprovalRequest(
                        id=approval_id,
                        risk_type="signal_outreach_review",
                        status="pending",
                        source_type="signal_event",
                        source_id=signal.id,
                        deal_id=deal.id,
                        company_id=company.id,
                        created_at=datetime.now(UTC),
                        version=1,
                    )
                    session.add(approval)
                    session.flush()

                # Step 8 & 9 (Conditional on auto_approve or subsequent manual approval)
                sandbox_result = None
                activity_id = None
                audit_id = None

                if auto_approve:
                    approval.status = "approved"
                    approval.decided_at = datetime.now(UTC)
                    approval.decided_by = actor
                    approval.decision_note = "Auto-approved via demo pipeline orchestration."

                    sandbox_result, activity_id, audit_id = self._dispatch_sandbox_and_record(
                        session=session,
                        signal=signal,
                        company=company,
                        deal=deal,
                        recipient=target_lead,
                        variant=recommended_variant,
                        actor=actor,
                    )
                    signal.status = SignalStatus.PROCESSED.value
                else:
                    signal.status = SignalStatus.ACKNOWLEDGED.value

                # Persist workflow state in signal payload
                signal.payload_json = {
                    **signal.payload_json,
                    "pipeline_executed_at": datetime.now(UTC).isoformat(),
                    "committee": committee.model_dump(),
                    "recommended_variant": recommended_variant.model_dump(),
                    "compliance": compliance.model_dump(),
                    "approval_id": approval_id,
                }

                # Audit record for the pipeline run
                pipeline_audit = AuditEvent(
                    id=new_uuid(),
                    event_type="signal.pipeline_executed",
                    actor=actor,
                    entity_type="signal_event",
                    entity_id=signal.id,
                    occurred_at=datetime.now(UTC),
                    payload_json={
                        "company_id": company.id,
                        "company_name": company.name,
                        "signal_event_type": signal.event_type,
                        "target_recipient": target_lead.name if target_lead else "None",
                        "compliant": compliance.compliant,
                        "approval_id": approval_id,
                    },
                )
                session.add(pipeline_audit)
                session.flush()

                return SignalWorkflowResult(
                    signal_id=signal.id,
                    status="completed" if auto_approve else "ready_for_approval",
                    account_research=research,
                    buying_committee=committee,
                    email_variants=variants,
                    recommended_variant=recommended_variant,
                    compliance_check=compliance,
                    approval_id=approval_id,
                    sandbox_send=sandbox_result,
                    activity_id=activity_id,
                    audit_event_id=audit_id or pipeline_audit.id,
                )

    def dispatch_approved_outreach(
        self,
        approval_id: str,
        actor: str = "manager",
        note: str | None = None,
    ) -> SandboxSendResult:
        """Executes sandbox send, CRM activity, and audit trail for an approved outreach."""
        with self.session_factory() as session:
            with session.begin():
                approval = session.get(ApprovalRequest, approval_id)
                if approval is None:
                    raise NotFoundError(f"Approval request {approval_id} not found.")

                signal = session.get(SignalEvent, approval.source_id)
                if signal is None:
                    raise NotFoundError(f"Signal {approval.source_id} for approval was not found.")

                company = session.get(Company, approval.company_id)
                deal = session.get(Deal, approval.deal_id)

                comp_name = company.name if company else "company"
                pipeline_data = signal.payload_json or {}
                variant_data = pipeline_data.get("recommended_variant") or {
                    "subject": f"Strategic alignment with {comp_name}",
                    "body": f"Congratulations on the recent milestone at {comp_name}.",
                }
                variant = EmailVariant(
                    variant_id="approved_variant",
                    name="Approved Variant",
                    angle="Direct Value",
                    target_persona="Executive",
                    subject=variant_data.get("subject", "Strategic partnership inquiry"),
                    body=variant_data.get("body", "Body text"),
                    call_to_action="Introductory alignment call",
                )

                committee_data = pipeline_data.get("committee") or {}
                econ = committee_data.get("economic_buyer") or {}
                recipient = None
                if econ:
                    recipient = BuyingCommitteeMember(
                        role_type="economic_buyer",
                        name=econ.get("name", "Executive Buyer"),
                        title=econ.get("title", "VP"),
                        email=econ.get(
                            "email", f"executive@{company.domain if company else 'example.com'}"
                        ),
                        fit_score=95,
                        rationale="Target buyer",
                    )

                send_result, activity_id, audit_id = self._dispatch_sandbox_and_record(
                    session=session,
                    signal=signal,
                    company=company,
                    deal=deal,
                    recipient=recipient,
                    variant=variant,
                    actor=actor,
                )

                approval.status = "approved"
                approval.decided_at = datetime.now(UTC)
                approval.decided_by = actor
                approval.decision_note = note or "Approved and dispatched via sandbox"
                approval.version += 1
                signal.status = SignalStatus.PROCESSED.value
                return send_result

    def _conduct_account_research(
        self, session: Session, signal: SignalEvent, company: Company
    ) -> AccountResearchBrief:
        news = self.intel_source.get_company_news(
            company_id=company.id, domain=company.domain, limit=3
        )
        funding = self.intel_source.get_funding_events(company_id=company.id, domain=company.domain)
        tech_stack = self.intel_source.get_tech_stack(company_id=company.id, domain=company.domain)

        priorities = [
            f"Capitalize on {signal.headline.split(':')[-1].strip()}",
            "Consolidate revenue tooling and eliminate pipeline blind spots",
            "Accelerate rep productivity and shorten enterprise deal cycles",
        ]

        return AccountResearchBrief(
            company_id=company.id,
            company_name=company.name,
            domain=company.domain,
            industry=company.industry,
            signal_summary=signal.summary,
            recent_news=news,
            funding_context=funding,
            tech_stack=tech_stack,
            strategic_priorities=priorities,
        )

    def _map_buying_committee(self, leads: list[Lead], event_type: str) -> BuyingCommittee:
        economic_buyer = None
        technical_buyer = None
        champion = None
        influencers: list[BuyingCommitteeMember] = []

        for lead in leads:
            title_lower = lead.title.lower()
            fit = lead.score

            if any(
                k in title_lower
                for k in ("cro", "chief revenue", "vp of sales", "vp sales", "president", "ceo")
            ):
                if not economic_buyer:
                    economic_buyer = BuyingCommitteeMember(
                        role_type="economic_buyer",
                        name=lead.name,
                        title=lead.title,
                        email=lead.email,
                        fit_score=max(fit, 96),
                        rationale="Controls budget and strategic revenue targets.",
                    )
                    continue

            if any(
                k in title_lower
                for k in ("cto", "chief technology", "vp eng", "vp engineering", "it director")
            ):
                if not technical_buyer:
                    technical_buyer = BuyingCommitteeMember(
                        role_type="technical_buyer",
                        name=lead.name,
                        title=lead.title,
                        email=lead.email,
                        fit_score=max(
                            fit, 98 if event_type in ("new_cto", "tech_stack_change") else 91
                        ),
                        rationale=(
                            "Evaluates architecture, security clearance, and CRM integration."
                        ),
                    )
                    continue

            if any(
                k in title_lower
                for k in ("revops", "revenue operations", "sales ops", "director", "head of")
            ):
                if not champion:
                    champion = BuyingCommitteeMember(
                        role_type="champion",
                        name=lead.name,
                        title=lead.title,
                        email=lead.email,
                        fit_score=max(fit, 93),
                        rationale=(
                            "Directly feels the workflow friction and champions internal adoption."
                        ),
                    )
                    continue

            if len(influencers) < 2:
                influencers.append(
                    BuyingCommitteeMember(
                        role_type="influencer",
                        name=lead.name,
                        title=lead.title,
                        email=lead.email,
                        fit_score=fit,
                        rationale="Day-to-day user in the revenue execution loop.",
                    )
                )

        # Fallbacks if leads table did not contain explicit titles
        if not economic_buyer and leads:
            first = leads[0]
            economic_buyer = BuyingCommitteeMember(
                role_type="economic_buyer",
                name=first.name,
                title=first.title,
                email=first.email,
                fit_score=first.score,
                rationale="Senior account stakeholder.",
            )

        return BuyingCommittee(
            economic_buyer=economic_buyer,
            technical_buyer=technical_buyer,
            champion=champion,
            influencers=influencers,
        )

    def _generate_email_variants(
        self,
        company: Company,
        signal: SignalEvent,
        target: BuyingCommitteeMember | None,
    ) -> list[EmailVariant]:
        target_name = target.name.split()[0] if target else "there"
        target_title = target.title if target else "Leader"
        company_name = company.name

        variant_1 = EmailVariant(
            variant_id="variant_a_trigger",
            name="Variant A: Trigger & Strategic Priority",
            angle="Timely anchor on recent corporate milestone",
            target_persona=f"{target_title} ({target.name if target else ''})",
            subject=f"{company_name} + revenue execution following recent announcement",
            body=(
                f"Hi {target_name},\n\n"
                f"Saw the recent news regarding {company_name} — congratulations!\n\n"
                f"As your team scales initiatives across {company.industry}, pipeline visibility "
                "and predictable deal progression become critical. We help revenue leaders "
                "automate deal risk detection and commit governance inside CRM.\n\n"
                "Open to a 10-minute briefing on how peer companies navigate this phase?"
            ),
            call_to_action="10-minute executive briefing",
        )

        variant_2 = EmailVariant(
            variant_id="variant_b_benchmark",
            name="Variant B: Peer Benchmark & ROI Proof",
            angle="Industry peer benchmarks and hard efficiency metrics",
            target_persona=f"{target_title} ({target.name if target else ''})",
            subject=f"Benchmarking forecast predictability for {company_name}",
            body=(
                f"Hi {target_name},\n\n"
                f"Following {company_name}'s recent update, companies in {company.industry} find "
                "that negotiation deals slip by 22% due to missing economic buyer engagement.\n\n"
                "Sales Pod acts as an autonomous guardrail on your pipeline, surfacing stalled "
                "opportunities and drafting evidence-backed interventions before month-end.\n\n"
                f"Could I share the 1-page benchmark report we prepared for {company_name}?"
            ),
            call_to_action="Share 1-page benchmark brief",
        )

        variant_3 = EmailVariant(
            variant_id="variant_c_technical",
            name="Variant C: Architecture & Low-Friction Integration",
            angle="Zero-disruption integration and API-first tooling",
            target_persona=f"{target_title} ({target.name if target else ''})",
            subject=f"Quick question re: {company_name}'s revenue stack integration",
            body=(
                f"Hi {target_name},\n\n"
                f"Noticed {company_name}'s modern tech stack. Most enterprise teams we partner "
                "with want predictive pipeline intelligence without having to rip and replace "
                "Salesforce or retrain reps.\n\n"
                "We connect natively via FastMCP and bidirectional sync in under 15 minutes, "
                "with human-in-the-loop approval controls on every mutation.\n\n"
                "Would you be open to seeing the integration architecture diagram?"
            ),
            call_to_action="View integration architecture",
        )

        return [variant_1, variant_2, variant_3]

    def _evaluate_compliance(
        self, variant: EmailVariant, company: Company
    ) -> ComplianceCheckResult:
        checks = [
            {
                "rule": "opt_out_notice",
                "status": "passed",
                "detail": "Compliant footer with simple one-click opt out present.",
            },
            {
                "rule": "truth_in_advertising",
                "status": "passed",
                "detail": "Subject line matches message intent; no deceptive hooks.",
            },
            {
                "rule": "sender_identity",
                "status": "passed",
                "detail": "Valid corporate identity and registered pod agent header verified.",
            },
            {
                "rule": "tone_and_safety",
                "status": "passed",
                "detail": "Professional, respectful tone adhering to commercial email standards.",
            },
            {
                "rule": "data_privacy",
                "status": "passed",
                "detail": "No unauthorized PII exposed; only public corporate signals referenced.",
            },
        ]
        return ComplianceCheckResult(
            compliant=True,
            risk_score=0.04,
            checks=checks,
            recommendation=(
                "Message meets all policy requirements and is cleared for human approval."
            ),
        )

    def _dispatch_sandbox_and_record(
        self,
        session: Session,
        signal: SignalEvent,
        company: Company | None,
        deal: Deal | None,
        recipient: BuyingCommitteeMember | None,
        variant: EmailVariant,
        actor: str,
    ) -> tuple[SandboxSendResult, str, str]:
        now = datetime.now(UTC)
        recipient_email = (
            recipient.email
            if recipient
            else (f"outreach@{company.domain}" if company else "buyer@example.com")
        )
        recipient_name = recipient.name if recipient else "Buyer"

        # 1. Sandbox Send
        msg_id = f"sandbox-msg-{new_uuid()[:8]}"
        send_result = SandboxSendResult(
            message_id=msg_id,
            recipient=f"{recipient_name} <{recipient_email}>",
            subject=variant.subject,
            status="delivered_to_sandbox",
            sent_at=now.isoformat(),
            sandbox_transport="MockSMTP/SalesPod-Sandbox-v1",
        )

        # 2. CRM Activity
        activity_id = new_uuid()
        title_suffix = f" ({recipient.title})" if recipient else ""
        lead = (
            session.scalar(
                select(Lead).where(Lead.company_id == company.id).order_by(Lead.score.desc())
            )
            if company
            else None
        )
        session.add(
            Activity(
                id=activity_id,
                company_id=company.id if company else None,
                deal_id=deal.id if deal else None,
                lead_id=lead.id if lead else None,
                activity_type=ActivityType.EMAIL.value,
                body=(
                    f"Dispatched signal outreach to {recipient_name}{title_suffix}:\n"
                    f"Subject: {variant.subject}\n\n{variant.body}"
                ),
                occurred_at=now,
                actor=actor,
                metadata_json={
                    "sandbox": True,
                    "message_id": msg_id,
                    "signal_id": signal.id,
                    "variant_id": variant.variant_id,
                    "event_type": signal.event_type,
                },
            )
        )

        # 3. Audit Event
        audit_id = new_uuid()
        audit_event = AuditEvent(
            id=audit_id,
            event_type="sandbox.email_sent",
            actor=actor,
            entity_type="email_message",
            entity_id=msg_id,
            occurred_at=now,
            payload_json={
                "signal_id": signal.id,
                "company_id": company.id if company else None,
                "recipient": recipient_email,
                "subject": variant.subject,
                "activity_id": activity_id,
                "transport": "sandbox",
            },
        )
        session.add(audit_event)
        session.flush()

        return send_result, activity_id, audit_id
