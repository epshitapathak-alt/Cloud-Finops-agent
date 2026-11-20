from typing import Dict, Any, List
from backend.app.database.models import ResourceModel, OptimizationProposalModel

class SafetyCriticAgent:
    """
    Independent Safety Critic Agent.
    Evaluates infrastructure safety risks before any proposal reaches human review.
    Cannot approve proposals or bypass the approval gate.
    """

    def evaluate_proposal(self, resource: ResourceModel, proposal: OptimizationProposalModel, tf_code: str) -> Dict[str, Any]:
        reasons = []
        is_blocked = False
        requires_approval = True
        risk_level = "LOW"

        env = (resource.environment or "development").lower()
        crit = (resource.criticality or "low").lower()
        tags = resource.tags or {}

        # Check 1: Explicit DO_NOT_MODIFY protection
        do_not_modify = str(tags.get("DO_NOT_MODIFY", "")).lower() == "true"
        if do_not_modify:
            is_blocked = True
            risk_level = "CRITICAL"
            reasons.append("PROHIBITED: Resource has an explicit 'DO_NOT_MODIFY=true' tag. Automation is blocked.")

        # Check 2: Production resource deletion
        is_production = env == "production"
        is_critical = crit in ("critical", "high")
        if is_production and "DELETE" in (proposal.recommended_action or ""):
            is_blocked = True
            risk_level = "CRITICAL"
            reasons.append("SAFETY VIOLATION: Automated deletion of production resources is strictly prohibited by security policy.")

        # Check 3: Critical Database modification
        if resource.resource_type == "RDS" and (is_production or is_critical):
            risk_level = "CRITICAL"
            reasons.append("HIGH DOWNTIME RISK: Modifying a production/critical database instance requires multi-team change advisory board (CAB) review.")

        # Check 4: Potential downtime during instance resize
        if proposal.recommended_action == "DOWNSIZE_INSTANCE" and is_production:
            if risk_level != "CRITICAL":
                risk_level = "HIGH"
            reasons.append("DOWNTIME WARNING: EC2 instance resize requires a reboot and temporary stop.")

        # Check 5: Public exposure & IAM safety check in Terraform code
        if "0.0.0.0/0" in tf_code and "ingress" in tf_code:
            is_blocked = True
            risk_level = "CRITICAL"
            reasons.append("SECURITY POLICY VIOLATION: Ingress rule exposes ports to public 0.0.0.0/0.")

        if "iam_role" in tf_code or "AdministratorAccess" in tf_code:
            is_blocked = True
            risk_level = "CRITICAL"
            reasons.append("SECURITY VIOLATION: Unauthorized IAM privilege alteration detected in Terraform template.")

        # Determine final decision
        if is_blocked:
            decision = "BLOCK"
            requires_approval = False # Blocked proposals cannot be approved
        elif risk_level in ("HIGH", "CRITICAL"):
            decision = "REQUIRE_APPROVAL"
            requires_approval = True
        elif is_production or env == "staging":
            decision = "REQUIRE_APPROVAL"
            requires_approval = True
            if risk_level == "LOW":
                risk_level = "MEDIUM"
            reasons.append(f"Standard compliance policy: All {env} modifications mandate human sign-off.")
        else:
            # Low risk non-production change
            decision = "ALLOW"
            requires_approval = True # FinOps guardrail: all infrastructure mutations require approval
            reasons.append("Safe non-production optimization opportunity.")

        return {
            "decision": decision,
            "risk_level": risk_level,
            "reasons": reasons,
            "requires_human_approval": requires_approval
        }
