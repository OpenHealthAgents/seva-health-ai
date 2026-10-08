from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class ObservationCreate(BaseModel):
    citizen_id: str
    code: str                  # e.g., "SYSTOLIC_BP", "HBA1C"
    value: float
    unit: str
    recorded_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "MANUAL_ENTRY"  # MANUAL_ENTRY | WEARABLE | LAB_REPORT


class Observation(ObservationCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    loinc_code: str
    display_name: str
    is_abnormal: bool = False


class VitalsPayload(BaseModel):
    """Vitals and lab bundle submitted during screening or follow-up."""
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    heart_rate: Optional[float] = None
    fasting_glucose: Optional[float] = None
    hba1c: Optional[float] = None
    total_cholesterol: Optional[float] = None
    hdl_cholesterol: Optional[float] = None
    triglycerides: Optional[float] = None
    bmi: Optional[float] = None
    waist_circumference: Optional[float] = None
    egfr: Optional[float] = None
