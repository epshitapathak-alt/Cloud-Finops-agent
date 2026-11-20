import pytest
from backend.app.database.models import ResourceModel, OptimizationProposalModel
from backend.app.services.simulation_engine import SimulationEngine
from backend.app.services.verification_engine import VerificationEngine

def test_simulation_blocked_without_approval():
    resource = ResourceModel(
        resource_id="i-unapproved-01",
        resource_name="unapproved-node",
        resource_type="EC2",
        instance_type="c5.4xlarge",
        monthly_cost=496.40,
        region="us-east-1",
        environment="development"
    )
    unapproved_proposal = OptimizationProposalModel(
        proposal_id="prop-unapp-01",
        resource_id="i-unapproved-01",
        recommended_action="DOWNSIZE_INSTANCE",
        recommended_configuration="c5.xlarge",
        estimated_saving=372.30,
        status="PENDING"
    )
    result = SimulationEngine.simulate_execution(resource, unapproved_proposal)
    assert result["status"] == "BLOCKED"
    assert "Explicit human approval is required" in result["error"]

def test_simulation_and_verification_when_approved():
    resource = ResourceModel(
        resource_id="i-approved-01",
        resource_name="approved-node",
        resource_type="EC2",
        instance_type="c5.4xlarge",
        monthly_cost=496.40,
        region="us-east-1",
        environment="development"
    )
    approved_proposal = OptimizationProposalModel(
        proposal_id="prop-app-01",
        resource_id="i-approved-01",
        recommended_action="DOWNSIZE_INSTANCE",
        recommended_configuration="c5.xlarge",
        estimated_saving=372.30,
        status="APPROVED"
    )
    sim = SimulationEngine.simulate_execution(resource, approved_proposal)
    assert sim["status"] == "SUCCESS"
    assert sim["cost_delta"] == -372.30
    assert sim["after_state"]["configuration"] == "c5.xlarge"

    ver = VerificationEngine.verify_remediation(sim["before_state"], sim["after_state"], sim["cost_delta"])
    assert ver["status"] == "VERIFIED"
    assert ver["drift_detected"] is False
