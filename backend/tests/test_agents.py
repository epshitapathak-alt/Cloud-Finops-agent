import pytest
from backend.app.database.models import ResourceModel, OptimizationProposalModel
from backend.app.agents.analyst_agent import AnalystAgent
from backend.app.agents.terraform_agent import TerraformAgent
from backend.app.agents.validator_agent import ValidatorAgent
from backend.app.agents.correction_agent import CorrectionAgent

def test_analyst_agent_fallback():
    agent = AnalystAgent()
    resource = ResourceModel(
        resource_id="i-test-analyst",
        resource_name="analytics-worker",
        resource_type="EC2",
        instance_type="c5.4xlarge",
        cpu_utilization=5.0,
        memory_utilization=12.0,
        monthly_cost=496.40,
        region="us-east-1",
        environment="development",
        resource_status="running",
        criticality="low"
    )
    proposal = agent.analyze_resource(resource)
    assert proposal.recommended_action == "DOWNSIZE_INSTANCE"
    assert proposal.estimated_saving > 0
    assert proposal.confidence >= 0.90
    assert proposal.source in ("GEMINI_AGENT", "DETERMINISTIC_FALLBACK")

def test_terraform_agent_and_validation():
    tf_agent = TerraformAgent()
    resource = ResourceModel(
        resource_id="i-test-tf",
        resource_name="worker-dev",
        resource_type="EC2",
        instance_type="c5.4xlarge",
        monthly_cost=496.40,
        region="us-east-1",
        environment="development"
    )
    proposal = OptimizationProposalModel(
        proposal_id="prop-test-123",
        resource_id="i-test-tf",
        recommended_action="DOWNSIZE_INSTANCE",
        recommended_configuration="c5.xlarge",
        estimated_saving=372.30
    )
    code = tf_agent.generate_terraform(resource, proposal)
    assert 'resource "aws_instance"' in code
    assert "c5.xlarge" in code

    validator = ValidatorAgent()
    val_res = validator.validate_code(code)
    assert val_res["status"] == "SUCCESS"
    assert val_res["exit_code"] == 0

def test_correction_agent_bounded_retry():
    corrector = CorrectionAgent()
    # Bad code with unbalanced brace
    broken_code = 'resource "aws_instance" "test" { ami = "ami-123" '
    res = corrector.run_correction_loop(broken_code)
    # The patch adds the missing closing brace and succeeds
    assert res["status"] == "SUCCESS"
    assert res["retry_count"] <= 3
