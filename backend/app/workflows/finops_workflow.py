import uuid
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from backend.app.workflows.state import FinOpsWorkflowState
from backend.app.agents.analyst_agent import AnalystAgent
from backend.app.agents.terraform_agent import TerraformAgent
from backend.app.agents.validator_agent import ValidatorAgent
from backend.app.agents.correction_agent import CorrectionAgent
from backend.app.agents.safety_critic_agent import SafetyCriticAgent
from backend.app.services.simulation_engine import SimulationEngine
from backend.app.services.verification_engine import VerificationEngine
from backend.app.database.models import ResourceModel, OptimizationProposalModel

analyst_agent = AnalystAgent()
terraform_agent = TerraformAgent()
validator_agent = ValidatorAgent()
correction_agent = CorrectionAgent()
safety_critic_agent = SafetyCriticAgent()

# Helper conversion from state dictionary to ResourceModel-like object
def dict_to_resource(d: Dict[str, Any]) -> ResourceModel:
    return ResourceModel(
        resource_id=d["resource_id"],
        resource_name=d.get("resource_name", d["resource_id"]),
        resource_type=d["resource_type"],
        instance_type=d.get("instance_type"),
        cpu_utilization=d.get("cpu_utilization", 0.0),
        memory_utilization=d.get("memory_utilization", 0.0),
        monthly_cost=d["monthly_cost"],
        region=d["region"],
        environment=d["environment"],
        resource_status=d.get("resource_status", "running"),
        criticality=d.get("criticality", "low"),
        last_activity=d.get("last_activity"),
        tags=d.get("tags", {})
    )

# --- Node Definitions ---

def analyze_node(state: FinOpsWorkflowState) -> Dict[str, Any]:
    res = dict_to_resource(state["resource_data"])
    proposal = analyst_agent.analyze_resource(res)
    prop_dict = proposal.model_dump()
    prop_dict["proposal_id"] = f"prop-{res.resource_id[-8:]}-{uuid.uuid4().hex[:6]}"
    
    events = list(state.get("audit_events", []))
    events.append({
        "node": "ANALYZE",
        "action": "METRICS_EVALUATED",
        "details": f"Analyzed {res.resource_id}: {proposal.recommended_action} (Savings: ${proposal.estimated_saving})"
    })
    return {
        "proposal_data": prop_dict,
        "audit_events": events
    }

def generate_terraform_node(state: FinOpsWorkflowState) -> Dict[str, Any]:
    res = dict_to_resource(state["resource_data"])
    prop_data = state["proposal_data"]
    prop_obj = OptimizationProposalModel(
        proposal_id=prop_data["proposal_id"],
        resource_id=res.resource_id,
        recommended_action=prop_data["recommended_action"],
        recommended_configuration=prop_data["recommended_configuration"]
    )
    code = terraform_agent.generate_terraform(res, prop_obj)
    
    events = list(state.get("audit_events", []))
    events.append({
        "node": "GENERATE_TERRAFORM",
        "action": "TERRAFORM_GENERATED",
        "details": f"Generated IaC configuration v1 for {res.resource_id}"
    })
    return {
        "terraform_code": code,
        "terraform_version": 1,
        "validation_attempts": [],
        "retry_count": 0,
        "audit_events": events
    }

def validate_node(state: FinOpsWorkflowState) -> Dict[str, Any]:
    code = state["terraform_code"]
    attempt_num = state.get("retry_count", 0) + 1
    val_res = validator_agent.validate_code(code, attempt=attempt_num)
    
    attempts = list(state.get("validation_attempts", []))
    attempts.append(val_res)
    
    events = list(state.get("audit_events", []))
    events.append({
        "node": "VALIDATE",
        "action": f"VALIDATION_ATTEMPT_{attempt_num}",
        "details": f"Result: {val_res['status']} (Exit Code {val_res['exit_code']})"
    })
    
    return {
        "validation_status": val_res["status"],
        "validation_attempts": attempts,
        "validation_error": val_res.get("stderr"),
        "audit_events": events
    }

def fix_node(state: FinOpsWorkflowState) -> Dict[str, Any]:
    current_code = state["terraform_code"]
    err = state.get("validation_error", "Syntax error")
    fixed_code = correction_agent._correct_code(current_code, err)
    new_retry = state.get("retry_count", 0) + 1
    
    events = list(state.get("audit_events", []))
    events.append({
        "node": "FIX",
        "action": "AUTONOMOUS_CORRECTION",
        "details": f"Applied automated patch iteration {new_retry}"
    })
    
    return {
        "terraform_code": fixed_code,
        "terraform_version": state.get("terraform_version", 1) + 1,
        "retry_count": new_retry,
        "audit_events": events
    }

def safety_check_node(state: FinOpsWorkflowState) -> Dict[str, Any]:
    res = dict_to_resource(state["resource_data"])
    prop_data = state["proposal_data"]
    prop_obj = OptimizationProposalModel(
        proposal_id=prop_data["proposal_id"],
        resource_id=res.resource_id,
        recommended_action=prop_data["recommended_action"],
        recommended_configuration=prop_data["recommended_configuration"]
    )
    decision = safety_critic_agent.evaluate_proposal(res, prop_obj, state["terraform_code"])
    
    events = list(state.get("audit_events", []))
    events.append({
        "node": "SAFETY_CHECK",
        "action": "SAFETY_CRITIC_EVALUATION",
        "details": f"Decision: {decision['decision']}, Risk: {decision['risk_level']}"
    })
    
    initial_approval = "PENDING"
    if decision["decision"] == "BLOCK":
        initial_approval = "BLOCKED"
        
    return {
        "safety_decision": decision,
        "approval_status": initial_approval,
        "audit_events": events
    }

def human_approval_checkpoint_node(state: FinOpsWorkflowState) -> Dict[str, Any]:
    events = list(state.get("audit_events", []))
    status = state.get("approval_status", "PENDING")
    events.append({
        "node": "HUMAN_APPROVAL_CHECKPOINT",
        "action": "APPROVAL_STATUS_EVALUATION",
        "details": f"Current status evaluated: {status}"
    })
    return {"audit_events": events}

def simulate_node(state: FinOpsWorkflowState) -> Dict[str, Any]:
    res = dict_to_resource(state["resource_data"])
    prop_data = state["proposal_data"]
    prop_obj = OptimizationProposalModel(
        proposal_id=prop_data["proposal_id"],
        resource_id=res.resource_id,
        recommended_action=prop_data["recommended_action"],
        recommended_configuration=prop_data["recommended_configuration"],
        estimated_saving=prop_data["estimated_saving"],
        status=state.get("approval_status", "APPROVED")
    )
    sim_res = SimulationEngine.simulate_execution(res, prop_obj)
    
    events = list(state.get("audit_events", []))
    events.append({
        "node": "SIMULATE",
        "action": "DRY_RUN_SIMULATION",
        "details": f"Simulation outcome: {sim_res['status']} (Delta: ${sim_res['cost_delta']})"
    })
    return {
        "simulation_result": sim_res,
        "audit_events": events
    }

def verify_node(state: FinOpsWorkflowState) -> Dict[str, Any]:
    sim = state["simulation_result"]
    ver_res = VerificationEngine.verify_remediation(
        sim["before_state"],
        sim["after_state"],
        sim["cost_delta"]
    )
    events = list(state.get("audit_events", []))
    events.append({
        "node": "VERIFY",
        "action": "POST_EXECUTION_VERIFICATION",
        "details": f"Verification status: {ver_res['status']} (Drift: {ver_res['drift_detected']})"
    })
    return {
        "verification_result": ver_res,
        "audit_events": events
    }

def audit_node(state: FinOpsWorkflowState) -> Dict[str, Any]:
    events = list(state.get("audit_events", []))
    status = "COMPLETED"
    if state.get("safety_decision", {}).get("decision") == "BLOCK":
        status = "SAFETY_BLOCKED"
    elif state.get("validation_status") != "SUCCESS":
        status = "VALIDATION_FAILED"
    elif state.get("approval_status") == "PENDING":
        status = "AWAITING_APPROVAL"
        
    events.append({
        "node": "AUDIT",
        "action": "WORKFLOW_PERSISTED",
        "details": f"Workflow finalized with status {status}"
    })
    return {
        "final_status": status,
        "audit_events": events
    }

# --- Conditional Edge Functions ---

def route_after_analyze(state: FinOpsWorkflowState) -> Literal["generate_terraform", "audit"]:
    prop = state.get("proposal_data", {})
    if prop.get("recommended_action") == "NO_ACTION":
        return "audit"
    return "generate_terraform"

def route_after_validate(state: FinOpsWorkflowState) -> Literal["safety_check", "fix", "audit"]:
    status = state.get("validation_status")
    if status == "SUCCESS":
        return "safety_check"
    # If failed and retry count < 3
    if state.get("retry_count", 0) < 3:
        return "fix"
    return "audit"

def route_after_safety(state: FinOpsWorkflowState) -> Literal["human_approval_checkpoint", "audit"]:
    decision = state.get("safety_decision", {}).get("decision")
    if decision == "BLOCK":
        return "audit"
    return "human_approval_checkpoint"

def route_after_approval(state: FinOpsWorkflowState) -> Literal["simulate", "audit"]:
    status = state.get("approval_status")
    if status == "APPROVED":
        return "simulate"
    return "audit"

# --- Build LangGraph Workflow ---

def create_finops_workflow():
    workflow = StateGraph(FinOpsWorkflowState)

    workflow.add_node("analyze", analyze_node)
    workflow.add_node("generate_terraform", generate_terraform_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("fix", fix_node)
    workflow.add_node("safety_check", safety_check_node)
    workflow.add_node("human_approval_checkpoint", human_approval_checkpoint_node)
    workflow.add_node("simulate", simulate_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("audit", audit_node)

    # Add Edges
    workflow.add_edge(START, "analyze")
    workflow.add_conditional_edges("analyze", route_after_analyze)
    workflow.add_edge("generate_terraform", "validate")
    workflow.add_conditional_edges("validate", route_after_validate)
    workflow.add_edge("fix", "validate")
    workflow.add_conditional_edges("safety_check", route_after_safety)
    workflow.add_conditional_edges("human_approval_checkpoint", route_after_approval)
    workflow.add_edge("simulate", "verify")
    workflow.add_edge("verify", "audit")
    workflow.add_edge("audit", END)

    return workflow.compile()
