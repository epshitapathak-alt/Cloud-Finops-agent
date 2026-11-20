from typing import Dict, Any
from backend.app.database.models import ResourceModel, OptimizationProposalModel, ExecutionSimulationModel

class SimulationEngine:
    @staticmethod
    def simulate_execution(resource: ResourceModel, proposal: OptimizationProposalModel) -> Dict[str, Any]:
        """
        Simulate the infrastructure change in a safe sandboxed dry-run mode.
        Enforces server-side rule: Optimization proposal MUST be APPROVED before simulation can execute.
        """
        if proposal.status != "APPROVED":
            return {
                "status": "BLOCKED",
                "error": f"Execution blocked: Proposal status is '{proposal.status}'. Explicit human approval is required.",
                "before_state": {},
                "after_state": {},
                "cost_delta": 0.0,
                "execution_log": f"[FINOPS-GUARD] Blocked unapproved execution attempt on resource {resource.resource_id}."
            }

        # Baseline before state
        before_state = {
            "resource_id": resource.resource_id,
            "resource_name": resource.resource_name,
            "resource_type": resource.resource_type,
            "configuration": resource.instance_type,
            "monthly_cost": resource.monthly_cost,
            "status": resource.resource_status,
            "region": resource.region,
            "environment": resource.environment
        }

        # Simulated after state
        after_state = dict(before_state)
        action = proposal.recommended_action
        cost_delta = -proposal.estimated_saving

        if action == "DOWNSIZE_INSTANCE":
            after_state["configuration"] = proposal.recommended_configuration
            after_state["monthly_cost"] = round(resource.monthly_cost - proposal.estimated_saving, 2)
            log_detail = f"Simulated EC2 API Call: ModifyInstanceAttribute({resource.resource_id}, InstanceType={proposal.recommended_configuration})"
        elif action == "DELETE_UNATTACHED_VOLUME":
            after_state["status"] = "deleted (safety snapshot preserved)"
            after_state["monthly_cost"] = 0.0
            log_detail = f"Simulated EBS API Call: CreateSnapshot({resource.resource_id}) -> DeleteVolume({resource.resource_id})"
        elif action == "DOWNSIZE_DATABASE":
            after_state["configuration"] = proposal.recommended_configuration
            after_state["monthly_cost"] = round(resource.monthly_cost - proposal.estimated_saving, 2)
            log_detail = f"Simulated RDS API Call: ModifyDBInstance({resource.resource_id}, DBInstanceClass={proposal.recommended_configuration}, ApplyImmediately=false)"
        elif action == "APPLY_S3_LIFECYCLE_TIER":
            after_state["configuration"] = "Glacier IR Transition Active"
            after_state["monthly_cost"] = round(resource.monthly_cost - proposal.estimated_saving, 2)
            log_detail = f"Simulated S3 API Call: PutBucketLifecycleConfiguration({resource.resource_id}, Tier=GLACIER_IR)"
        else:
            log_detail = f"Simulated No-Op on {resource.resource_id}"

        execution_log = f"""[DRY-RUN SIMULATION] Started execution for proposal {proposal.proposal_id}
[AUTH CHECK] Human approval confirmed (Approver verified).
[ACTION] {action} on {resource.resource_id}
[API DISPATCH] {log_detail}
[COST IMPACT] Baseline: ${resource.monthly_cost:.2f}/mo -> Projected: ${after_state['monthly_cost']:.2f}/mo (Savings: ${proposal.estimated_saving:.2f}/mo)
[DRY-RUN SUCCESS] Simulated state transition verified with zero AWS mutations.
"""

        return {
            "status": "SUCCESS",
            "before_state": before_state,
            "after_state": after_state,
            "cost_delta": cost_delta,
            "execution_log": execution_log
        }
