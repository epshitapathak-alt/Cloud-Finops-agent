from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class SafetyDecisionResponse(BaseModel):
    decision: str
    risk_level: str
    reasons: List[str] = []
    requires_human_approval: bool = True
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SimulationResponse(BaseModel):
    id: int
    proposal_id: str
    mode: str
    status: str
    before_state: dict
    after_state: dict
    cost_delta: float
    execution_log: Optional[str] = None
    executed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VerificationResponse(BaseModel):
    id: int
    simulation_id: int
    status: str
    expected_state: dict
    observed_state: dict
    drift_detected: bool
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)
