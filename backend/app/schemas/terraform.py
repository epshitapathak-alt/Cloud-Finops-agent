from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class ValidationAttemptResponse(BaseModel):
    attempt_number: int
    command: str
    exit_code: int
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TerraformVersionResponse(BaseModel):
    version: int
    code: str
    file_path: Optional[str] = None
    created_at: datetime
    validation_attempts: List[ValidationAttemptResponse] = []

    model_config = ConfigDict(from_attributes=True)
