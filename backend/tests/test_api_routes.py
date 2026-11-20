import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import init_db

@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

def test_resources_and_overview(client):
    res_seed = client.post("/api/resources/seed?force_reload=true")
    assert res_seed.status_code == 200

    res_list = client.get("/api/resources")
    assert res_list.status_code == 200
    resources = res_list.json()
    assert len(resources) > 0

    res_ov = client.get("/api/overview")
    assert res_ov.status_code == 200
    overview = res_ov.json()
    assert overview["total_cloud_cost"] > 0
    assert overview["resources_analyzed"] > 0

def test_analysis_run_and_approval_flow(client):
    run_res = client.post("/api/analysis/run")
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["status"] == "COMPLETED"
    assert len(run_data["proposal_ids"]) > 0

    target_prop_id = run_data["proposal_ids"][0]

    # Verify unapproved execution is forbidden (403)
    sim_blocked = client.post(f"/api/optimizations/{target_prop_id}/simulate")
    assert sim_blocked.status_code == 403

    # Approve proposal
    app_res = client.post(
        f"/api/optimizations/{target_prop_id}/approve",
        json={"approver": "TestQAEngineer", "reason": "Automated integration test approval"}
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVED"

    # Simulate execution
    sim_res = client.post(f"/api/optimizations/{target_prop_id}/simulate")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["simulation"]["status"] == "SUCCESS"
    assert sim_data["verification"]["status"] == "VERIFIED"

    # Audit logs verification
    audit_res = client.get("/api/audit-logs")
    assert audit_res.status_code == 200
    assert len(audit_res.json()) > 0
