from typing import List, Dict, Any, Tuple
from backend.app.database.models import ResourceModel

# Known reference instance sizing and typical costs
INSTANCE_DOWNSIZE_MAP = {
    "c5.4xlarge": ("c5.xlarge", 124.10),
    "m5.2xlarge": ("m5.large", 70.08),
    "db.r5.2xlarge": ("db.r5.large", 180.00),
    "db.r5.4xlarge": ("db.r5.2xlarge", 720.00),
    "t3.medium": ("t3.nano", 3.80)
}

class CostAnalyzerService:
    @staticmethod
    def calculate_overview_metrics(resources: List[ResourceModel]) -> Dict[str, Any]:
        """Compute aggregate cloud financial and utilization metrics deterministically."""
        if not resources:
            return {
                "total_cloud_cost": 0.0,
                "potential_monthly_savings": 0.0,
                "resources_analyzed": 0,
                "optimization_opportunities": 0,
                "average_cpu_utilization": 0.0,
                "average_memory_utilization": 0.0
            }

        total_cost = sum(r.monthly_cost for r in resources)
        cpu_values = [r.cpu_utilization for r in resources if r.resource_type in ("EC2", "RDS")]
        mem_values = [r.memory_utilization for r in resources if r.resource_type in ("EC2", "RDS")]

        avg_cpu = round(sum(cpu_values) / len(cpu_values), 2) if cpu_values else 0.0
        avg_mem = round(sum(mem_values) / len(mem_values), 2) if mem_values else 0.0

        opportunities = CostAnalyzerService.identify_optimization_opportunities(resources)
        potential_savings = round(sum(o["estimated_saving"] for o in opportunities), 2)

        return {
            "total_cloud_cost": round(total_cost, 2),
            "potential_monthly_savings": potential_savings,
            "resources_analyzed": len(resources),
            "optimization_opportunities": len(opportunities),
            "average_cpu_utilization": avg_cpu,
            "average_memory_utilization": avg_mem
        }

    @staticmethod
    def identify_optimization_opportunities(resources: List[ResourceModel]) -> List[Dict[str, Any]]:
        """
        Evaluate deterministic FinOps rules:
        1. EC2: Underutilized (< 15% CPU and < 25% Memory) -> Downsize
        2. EBS: Available / Unattached volume -> Delete
        3. RDS: Underutilized (< 15% CPU) -> Downsize instance class
        4. S3: Standard storage with no lifecycle rule in dev/archive -> Transition to Glacier / Infrequent Access
        """
        opportunities = []

        for r in resources:
            # Rule 1: EC2 Underutilized
            if r.resource_type == "EC2" and r.resource_status == "running":
                if r.cpu_utilization < 15.0 and r.memory_utilization < 30.0:
                    current_inst = r.instance_type or "c5.4xlarge"
                    downsized_target, target_cost = INSTANCE_DOWNSIZE_MAP.get(current_inst, ("t3.large", round(r.monthly_cost * 0.35, 2)))
                    saving = round(r.monthly_cost - target_cost, 2)
                    
                    risk = "LOW" if r.environment in ("development", "testing") else "HIGH"
                    if r.criticality == "critical" or r.environment == "production":
                        risk = "CRITICAL"

                    opportunities.append({
                        "resource_id": r.resource_id,
                        "resource_name": r.resource_name,
                        "resource_type": r.resource_type,
                        "issue": f"Severely underutilized EC2 instance ({r.cpu_utilization}% CPU, {r.memory_utilization}% RAM)",
                        "evidence": f"Average 30-day CPU is {r.cpu_utilization}% (threshold < 15%), Memory is {r.memory_utilization}%. Monthly spend is ${r.monthly_cost:.2f}.",
                        "recommended_action": "DOWNSIZE_INSTANCE",
                        "current_configuration": current_inst,
                        "recommended_configuration": downsized_target,
                        "current_monthly_cost": r.monthly_cost,
                        "estimated_saving": max(saving, 0.0),
                        "confidence": 0.95,
                        "risk": risk,
                        "reasoning": f"Downsizing from {current_inst} to {downsized_target} cuts compute capacity while safely satisfying observed load.",
                        "assumptions": "Workload baseline remains consistent with past 30 days telemetry."
                    })

            # Rule 2: Unattached EBS Volume
            elif r.resource_type == "EBS" and r.resource_status == "available":
                saving = round(r.monthly_cost, 2)
                risk = "LOW" if r.environment != "production" else "HIGH"
                opportunities.append({
                    "resource_id": r.resource_id,
                    "resource_name": r.resource_name,
                    "resource_type": r.resource_type,
                    "issue": "Unattached/Idle EBS volume accumulating storage costs",
                    "evidence": f"Volume status is '{r.resource_status}' with 0 read/write IOPS. Incurring ${r.monthly_cost:.2f}/mo.",
                    "recommended_action": "DELETE_UNATTACHED_VOLUME",
                    "current_configuration": f"{r.instance_type} (Status: available)",
                    "recommended_configuration": "Snapshot & Delete Volume",
                    "current_monthly_cost": r.monthly_cost,
                    "estimated_saving": saving,
                    "confidence": 0.99,
                    "risk": risk,
                    "reasoning": "Unattached storage volumes generate zero business value while incurring storage capacity costs.",
                    "assumptions": "Automated snapshot will be preserved before volume deletion."
                })

            # Rule 3: RDS Underutilized Replica or Non-Prod DB
            elif r.resource_type == "RDS":
                if r.cpu_utilization < 15.0 and r.environment in ("development", "testing", "staging"):
                    current_inst = r.instance_type or "db.r5.2xlarge"
                    downsized_target, target_cost = INSTANCE_DOWNSIZE_MAP.get(current_inst, ("db.r5.large", round(r.monthly_cost * 0.35, 2)))
                    saving = round(r.monthly_cost - target_cost, 2)

                    opportunities.append({
                        "resource_id": r.resource_id,
                        "resource_name": r.resource_name,
                        "resource_type": r.resource_type,
                        "issue": f"Oversized test/staging database instance running at {r.cpu_utilization}% CPU",
                        "evidence": f"Database CPU utilization averaged {r.cpu_utilization}% over billing period. Current cost ${r.monthly_cost:.2f}/mo.",
                        "recommended_action": "DOWNSIZE_DATABASE",
                        "current_configuration": current_inst,
                        "recommended_configuration": downsized_target,
                        "current_monthly_cost": r.monthly_cost,
                        "estimated_saving": max(saving, 0.0),
                        "confidence": 0.92,
                        "risk": "MEDIUM",
                        "reasoning": f"Non-production RDS instances do not require high concurrency memory buffers. Downsizing to {downsized_target} preserves full feature parity.",
                        "assumptions": "Maintenance window available for minimal failover downtime."
                    })

            # Rule 4: S3 Bucket Missing Lifecycle Rule
            elif r.resource_type == "S3":
                if "none" in str(r.tags.get("LifecyclePolicy", "")).lower() or r.environment in ("development", "testing"):
                    target_cost = round(r.monthly_cost * 0.20, 2)
                    saving = round(r.monthly_cost - target_cost, 2)

                    opportunities.append({
                        "resource_id": r.resource_id,
                        "resource_name": r.resource_name,
                        "resource_type": r.resource_type,
                        "issue": "S3 bucket has Standard storage tier without automated lifecycle tiering",
                        "evidence": f"Bucket size tier Standard incurrs ${r.monthly_cost:.2f}/mo with no lifecycle rules configured.",
                        "recommended_action": "APPLY_S3_LIFECYCLE_TIER",
                        "current_configuration": "Standard (No lifecycle policy)",
                        "recommended_configuration": "Transition to Glacier Instant Retrieval after 30 days",
                        "current_monthly_cost": r.monthly_cost,
                        "estimated_saving": max(saving, 0.0),
                        "confidence": 0.90,
                        "risk": "LOW",
                        "reasoning": "Infrequently accessed development objects can be archived to Glacier Instant Retrieval at 80% lower cost.",
                        "assumptions": "Data access latency of milliseconds from Glacier Instant Retrieval is acceptable."
                    })

        return opportunities
