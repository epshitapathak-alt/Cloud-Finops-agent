from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime

class AuditLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    action: str
    actor: str
    details: Dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class OverviewMetricsResponse(BaseModel):
    total_cloud_cost: float
    potential_monthly_savings: float
    resources_analyzed: int
    optimization_opportunities: int
    pending_approvals: int
    successful_validations: int
    average_cpu_utilization: float
    average_memory_utilization: float
