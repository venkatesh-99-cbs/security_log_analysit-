from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Any
from ..core.constants import LogSeverity, IncidentStatus

class SecurityLogBase(BaseModel):
    timestamp: datetime
    source: str
    category: str
    severity: LogSeverity
    message: str
    raw_data: Optional[dict] = None

class SecurityLogCreate(SecurityLogBase):
    file_id: int

class SecurityLog(SecurityLogBase):
    id: int
    file_id: int
    model_config = ConfigDict(from_attributes=True)

class IncidentBase(BaseModel):
    title: str
    description: str
    status: IncidentStatus
    severity: LogSeverity

class IncidentCreate(IncidentBase):
    pass

class Incident(IncidentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AIAnalysisBase(BaseModel):
    query: str
    response: str
    analysis_type: str

class AIAnalysis(AIAnalysisBase):
    id: int
    incident_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
