from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

from packages.types.enums import TriageUrgency, ClinicianReviewStatus


class SOAPReport(BaseModel):
    """Clinical SOAP Note synthesized by AI agent for physician review (adapted from refactoragent)."""
    subjective: str
    objective: str
    assessment: str
    plan: str
    key_observations: Dict[str, Any] = {}


class ClinicalTriageCase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    citizen_id: str
    citizen_name: str
    risk_assessment_id: str
    urgency: TriageUrgency
    escalation_reason: str
    soap_note: SOAPReport
    status: ClinicianReviewStatus = ClinicianReviewStatus.PENDING
    assigned_clinician_id: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
