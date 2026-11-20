import pytest
from backend.app.workflows.finops_workflow import create_finops_workflow
from backend.app.workflows.state import FinOpsWorkflowState

def test_langgraph_workflow_execution():
    workflow = create_finops_workflow()

    initial_state: FinOpsWorkflowState = {
        "run_id": "test-run-wf",
        "resource_id": "i-09ab7c12f4581ea01",
        "resource_data": {
            "resource_id": "i-09ab7c12f4581ea01",
            "resource_name": "analytics-worker-dev-01",
            "resource_type": "EC2",
            "instance_type": "c5.4xlarge",
            "cpu_utilization": 4.2,
            "memory_utilization": 11.5,
            "monthly_cost": 496.40,
            "region": "us-east-1",
            "environment": "development",
            "resource_status": "running",
            "criticality": "low",
            "tags": {"Environment": "development"}
        },
        "analysis_opportunity": None,
        "proposal_data": None,
        "terraform_code": None,
        "terraform_version": 1,
        "validation_status": None,
        "validation_attempts": [],
        "validation_error": None,
        "retry_count": 0,
        "safety_decision": None,
        "approval_status": "PENDING",
        "approver": None,
        "simulation_result": None,
        "verification_result": None,
        "final_status": "PENDING",
        "errors": [],
        "audit_events": []
    }

    # Run the compiled LangGraph workflow
    result = workflow.invoke(initial_state)

    assert result["proposal_data"] is not None
    assert result["proposal_data"]["recommended_action"] == "DOWNSIZE_INSTANCE"
    assert result["terraform_code"] is not None
    assert result["validation_status"] == "SUCCESS"
    assert result["safety_decision"] is not None
    assert result["final_status"] == "AWAITING_APPROVAL"
    assert len(result["audit_events"]) >= 5
