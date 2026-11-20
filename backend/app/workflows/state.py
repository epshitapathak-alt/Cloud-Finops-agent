from typing import TypedDict, List, Dict, Any, Optional

class FinOpsWorkflowState(TypedDict):
    run_id: str
    resource_id: str
    resource_data: Dict[str, Any]
    
    # Analyst stage
    analysis_opportunity: Optional[Dict[str, Any]]
    proposal_data: Optional[Dict[str, Any]]
    
    # Terraform stage
    terraform_code: Optional[str]
    terraform_version: int
    validation_status: Optional[str] # SUCCESS, FAILED, RETRY_LIMIT_REACHED
    validation_attempts: List[Dict[str, Any]]
    validation_error: Optional[str]
    retry_count: int
    
    # Safety critic stage
    safety_decision: Optional[Dict[str, Any]] # ALLOW, REQUIRE_APPROVAL, BLOCK
    
    # Approval checkpoint stage
    approval_status: str # PENDING, APPROVED, REJECTED, BLOCKED
    approver: Optional[str]
    
    # Simulation & Verification
    simulation_result: Optional[Dict[str, Any]]
    verification_result: Optional[Dict[str, Any]]
    
    # Audit & Status
    final_status: str
    errors: List[str]
    audit_events: List[Dict[str, Any]]
