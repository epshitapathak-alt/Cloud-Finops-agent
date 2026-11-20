import pytest
from backend.app.database.models import ResourceModel
from backend.app.services.cost_analyzer import CostAnalyzerService

def test_deterministic_cost_calculations():
    resources = [
        ResourceModel(
            resource_id="i-test-01",
            resource_name="dev-worker",
            resource_type="EC2",
            instance_type="c5.4xlarge",
            cpu_utilization=4.0,
            memory_utilization=10.0,
            monthly_cost=500.0,
            region="us-east-1",
            environment="development",
            resource_status="running",
            criticality="low"
        ),
        ResourceModel(
            resource_id="vol-test-02",
            resource_name="unused-vol",
            resource_type="EBS",
            instance_type="gp2-500GB",
            cpu_utilization=0.0,
            memory_utilization=0.0,
            monthly_cost=50.0,
            region="us-east-1",
            environment="development",
            resource_status="available",
            criticality="low"
        )
    ]

    metrics = CostAnalyzerService.calculate_overview_metrics(resources)
    assert metrics["total_cloud_cost"] == 550.0
    assert metrics["resources_analyzed"] == 2
    assert metrics["optimization_opportunities"] == 2
    assert metrics["potential_monthly_savings"] > 0
    assert metrics["average_cpu_utilization"] == 4.0
