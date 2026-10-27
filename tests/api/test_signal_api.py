from __future__ import annotations

from fastapi.testclient import TestClient

from salespod.interfaces.http.api import create_app


def test_simulate_signal_endpoint(seeded_service) -> None:
    app = create_app(seeded_service)
    client = TestClient(app)

    response = client.post("/api/signals/simulate", json={"event_type": "new_cto"})
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "new_cto"
    assert "Chief Technology Officer" in data["headline"]
    assert data["relevance_score"] >= 85


def test_seed_stream_endpoint(seeded_service) -> None:
    app = create_app(seeded_service)
    client = TestClient(app)

    response = client.post("/api/signals/stream/seed", json={})
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 5


def test_pipeline_execution_and_approval_inbox_flow(seeded_service) -> None:
    app = create_app(seeded_service)
    client = TestClient(app)

    # 1. Simulate a signal
    sim_res = client.post("/api/signals/simulate", json={"event_type": "funding_round"})
    assert sim_res.status_code == 200
    signal_id = sim_res.json()["id"]

    # 2. Run the 9-stage pipeline
    pipeline_res = client.post(f"/api/signals/{signal_id}/pipeline", json={"auto_approve": False})
    assert pipeline_res.status_code == 200
    pipeline_data = pipeline_res.json()
    assert pipeline_data["status"] == "ready_for_approval"
    approval_id = pipeline_data["approval_id"]
    assert approval_id is not None

    # 3. Check that it appears in /api/approvals
    approvals_res = client.get("/api/approvals")
    assert approvals_res.status_code == 200
    all_approvals = approvals_res.json()
    signal_approval = next((a for a in all_approvals if a["id"] == approval_id), None)
    assert signal_approval is not None
    assert signal_approval["status"] == "pending"
    assert signal_approval["risk_type"] == "signal_outreach_review"

    # 4. Decide "approved" via approval inbox endpoint
    decide_res = client.post(
        f"/api/approvals/{approval_id}/decision",
        json={
            "decision": "approved",
            "actor": "demo_manager",
            "note": "Looks great, send outreach",
        },
    )
    assert decide_res.status_code == 200
    decided_data = decide_res.json()
    assert decided_data["status"] == "approved"

    # 5. Verify audit events log the sandbox send
    audit_res = client.get("/api/audit/events")
    assert audit_res.status_code == 200
    audits = audit_res.json()
    event_types = {a["event_type"] for a in audits}
    assert "sandbox.email_sent" in event_types
