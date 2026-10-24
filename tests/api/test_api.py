from __future__ import annotations

from fastapi.testclient import TestClient

from salespod.infrastructure.seed.generator import stable_id
from salespod.interfaces.http.api import create_app


def test_dashboard_leads_and_approvals_are_backed_by_seeded_crm(seeded_service) -> None:
    client = TestClient(create_app(seeded_service))

    assert client.get("/api/health").json() == {"status": "ok", "database": "ok"}
    cors = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert cors.status_code == 200
    assert cors.headers["access-control-allow-origin"] == "http://localhost:5173"

    overview = client.get("/api/dashboard/overview")
    assert overview.status_code == 200
    overview_body = overview.json()
    assert overview_body["pipeline_totals"]["total_count"] == 120
    assert len(overview_body["stage_summaries"]) == 6
    assert overview_body["risk_counts"] == {
        "total": 5,
        "pending": 5,
        "approved": 0,
        "rejected": 0,
        "by_type": {"missing_economic_buyer": 5},
    }
    assert len(overview_body["recent_activities"]) == 10

    leads = client.get("/api/leads", params={"query": "example.com", "limit": 3})
    assert leads.status_code == 200
    assert len(leads.json()["items"]) == 3

    approvals = client.get("/api/approvals")
    assert approvals.status_code == 200
    assert len(approvals.json()) == 5
    approval_id = approvals.json()[0]["id"]
    decision = client.post(
        f"/api/approvals/{approval_id}/decision",
        json={"decision": "approved", "actor": "manager", "note": "Reviewed evidence."},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"


def test_deal_stage_and_agent_endpoints_use_existing_application_flows(seeded_service) -> None:
    client = TestClient(create_app(seeded_service))
    deal_id = stable_id("deal", 0)

    deal = client.get(f"/api/deals/{deal_id}")
    assert deal.status_code == 200
    assert deal.json()["deal"]["version"] == 1

    stage = client.post(
        f"/api/deals/{deal_id}/stage",
        json={
            "new_stage": "closed_lost",
            "reason": "The economic buyer was not confirmed.",
            "actor": "manager",
            "expected_version": 1,
            "idempotency_key": "api-stage-test-0",
        },
    )
    assert stage.status_code == 200
    assert stage.json()["deal"]["stage"] == "closed_lost"
    assert stage.json()["deal"]["version"] == 2

    agent = client.post("/api/agent/ask", json={"request": "Show the current pipeline snapshot"})
    assert agent.status_code == 200
    assert agent.json()["intent"] == "pipeline_snapshot"
    assert "Pipeline has 120 deal(s)" in agent.json()["response"]


def test_api_maps_crm_errors_to_stable_http_responses(seeded_service) -> None:
    client = TestClient(create_app(seeded_service))

    missing = client.get("/api/deals/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"

    invalid_limit = client.get("/api/leads", params={"limit": 0})
    assert invalid_limit.status_code == 422


def test_approval_decision_and_audit_events_survive_a_new_app_instance(seeded_service) -> None:
    first_client = TestClient(create_app(seeded_service))
    approval = first_client.get("/api/approvals").json()[0]
    decision = first_client.post(
        f"/api/approvals/{approval['id']}/decision",
        json={"decision": "approved", "actor": "manager", "note": "Evidence reviewed."},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    second_client = TestClient(create_app(seeded_service))
    persisted = second_client.get("/api/approvals").json()
    restored = next(item for item in persisted if item["id"] == approval["id"])
    assert restored["status"] == "approved"
    assert restored["decided_by"] == "manager"

    audit = second_client.get("/api/audit/events", params={"limit": 20})
    assert audit.status_code == 200
    assert any(item["event_type"] == "approval.decided" for item in audit.json())


def test_policy_endpoint_and_q4_supervisor_flow_are_actionable(seeded_service) -> None:
    client = TestClient(create_app(seeded_service))
    policy = client.post(
        "/api/policy/evaluate",
        json={"action": "discount", "discount_percent": 20},
    )
    assert policy.status_code == 200
    assert policy.json()["outcome"] == "requires_approval"

    answer = client.post("/api/agent/ask", json={"request": "Why will we miss Q4?"})
    assert answer.status_code == 200
    assert answer.json()["intent"] == "q4_risk"
    assert "economic buyer" in answer.json()["response"].lower()
