from __future__ import annotations

from sqlalchemy import select

from salespod.application.signal_stream import SignalStreamService
from salespod.application.signal_workflow import SignalWorkflowOrchestrator
from salespod.infrastructure.db.models import Activity, ApprovalRequest, AuditEvent, SignalEvent


def test_signal_workflow_full_pipeline_to_approval(seeded_service) -> None:
    session_factory = seeded_service.session_factory
    with session_factory() as session:
        with session.begin():
            stream = SignalStreamService(session)
            sig = stream.simulate_event(event_type="new_cto")
            signal_id = sig.id

    orchestrator = SignalWorkflowOrchestrator(session_factory)
    result = orchestrator.execute_pipeline(signal_id=signal_id, auto_approve=False)

    assert result.signal_id == signal_id
    assert result.status == "ready_for_approval"

    # 1. Research
    assert result.account_research.company_name is not None
    assert len(result.account_research.recent_news) > 0
    assert "technologies" in result.account_research.tech_stack

    # 2. Buying committee
    committee = result.buying_committee
    assert committee.economic_buyer is not None or committee.technical_buyer is not None

    # 3. Variants
    assert len(result.email_variants) == 3
    assert result.recommended_variant.subject is not None

    # 4. Compliance check
    assert result.compliance_check.compliant is True
    assert result.compliance_check.risk_score < 0.1

    # 5. Approval inbox item created
    with session_factory() as session:
        approval = session.scalar(
            select(ApprovalRequest).where(ApprovalRequest.source_id == signal_id)
        )
        assert approval is not None
        assert approval.risk_type == "signal_outreach_review"
        assert approval.status == "pending"


def test_signal_workflow_full_pipeline_with_approval_and_sandbox_dispatch(seeded_service) -> None:
    session_factory = seeded_service.session_factory
    with session_factory() as session:
        with session.begin():
            stream = SignalStreamService(session)
            sig = stream.simulate_event(event_type="funding_round")
            signal_id = sig.id

    orchestrator = SignalWorkflowOrchestrator(session_factory)
    # Run pipeline with auto_approve=True to simulate the full send loop
    result = orchestrator.execute_pipeline(signal_id=signal_id, auto_approve=True)

    assert result.status == "completed"
    assert result.sandbox_send is not None
    assert result.sandbox_send.status == "delivered_to_sandbox"
    assert "MockSMTP" in result.sandbox_send.sandbox_transport

    with session_factory() as session:
        # Check signal status
        updated_sig = session.get(SignalEvent, signal_id)
        assert updated_sig is not None
        assert updated_sig.status == "processed"

        # Check CRM Activity appended
        activities = session.scalars(
            select(Activity).where(Activity.activity_type == "email")
        ).all()
        assert len(activities) > 0
        latest_act = activities[-1]
        assert "Dispatched signal" in latest_act.body

        # Check AuditEvent
        audits = session.scalars(
            select(AuditEvent).where(AuditEvent.event_type == "sandbox.email_sent")
        ).all()
        assert len(audits) > 0
