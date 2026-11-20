import pytest
from backend.app.database.models import ResourceModel, OptimizationProposalModel
from backend.app.agents.safety_critic_agent import SafetyCriticAgent

def test_safety_critic_blocks_production_deletion():
    critic = SafetyCriticAgent()
    prod_resource = ResourceModel(
        resource_id="vol-prod-999",
        resource_name="prod-backup-vol",
        resource_type="EBS",
        instance_type="gp2-100GB",
        monthly_cost=100.0,
        region="us-east-1",
        environment="production",
        resource_status="available",
        criticality="high",
        tags={"Environment": "production"}
    )
    proposal = OptimizationProposalModel(
        proposal_id="prop-del-prod",
        resource_id="vol-prod-999",
        recommended_action="DELETE_UNATTACHED_VOLUME",
        recommended_configuration="Delete Volume",
        estimated_saving=100.0
    )
    result = critic.evaluate_proposal(prod_resource, proposal, "# dummy tf")
    assert result["decision"] == "BLOCK"
    assert result["risk_level"] == "CRITICAL"
    assert any("prohibited" in r.lower() for r in result["reasons"])

def test_safety_critic_flags_do_not_modify_tag():
    critic = SafetyCriticAgent()
    resource = ResourceModel(
        resource_id="i-tagged-resource",
        resource_name="sensitive-bastion",
        resource_type="EC2",
        instance_type="m5.2xlarge",
        monthly_cost=280.0,
        region="us-east-1",
        environment="development",
        tags={"DO_NOT_MODIFY": "true"}
    )
    proposal = OptimizationProposalModel(
        proposal_id="prop-tag",
        resource_id="i-tagged-resource",
        recommended_action="DOWNSIZE_INSTANCE",
        recommended_configuration="m5.large",
        estimated_saving=140.0
    )
    result = critic.evaluate_proposal(resource, proposal, "# dummy tf")
    assert result["decision"] == "BLOCK"
