from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

class OptimizationProposalBase(BaseModel):
    resource_id: str
    issue: str
    evidence: str
    recommended_action: str
    current_configuration: str
    recommended_configuration: str
    current_monthly_cost: float
    estimated_saving: float
    confidence: float = 0.90
    risk: str = "LOW"
    reasoning: str
    assumptions: Optional[str] = None
    source: str = "DETERMINISTIC_FALLBACK"

class OptimizationProposalCreate(OptimizationProposalBase):
    proposal_id: str
    run_id: Optional[str] = None

class OptimizationProposalResponse(OptimizationProposalBase):
    id: int
    proposal_id: str
    run_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApprovalActionRequest(BaseModel):
    approver: str = "LeadFinOpsEngineer"
    reason: Optional[str] = None
