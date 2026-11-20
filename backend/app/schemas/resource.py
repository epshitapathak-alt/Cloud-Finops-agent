from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class ResourceBase(BaseModel):
    resource_id: str
    resource_name: str
    resource_type: str
    instance_type: Optional[str] = None
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    monthly_cost: float
    region: str
    environment: str
    resource_status: str = "running"
    criticality: str = "low"
    last_activity: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict)

class ResourceCreate(ResourceBase):
    pass

class ResourceResponse(ResourceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
