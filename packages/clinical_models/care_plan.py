from datetime import datetime, date, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

from packages.types.enums import InterventionPillar


class DailyTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    day: int                          # 1 to 30
    pillar: InterventionPillar
    title: str
    description: str
    target_metric: Optional[str] = None
    completed: bool = False
    completed_at: Optional[datetime] = None


class CarePlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    citizen_id: str
    risk_assessment_id: str
    title: str
    focus_domain: str                 # e.g., "Metabolic Balance & Blood Pressure Control"
    start_date: date
    end_date: date
    adherence_percentage: float = 0.0 # Completed tasks / total tasks
    nutrition_guidance: str
    activity_guidance: str
    sleep_guidance: str = "Consistent 7-8 hours nightly sleep with screen cutoff 45 mins prior."
    stress_guidance: str = "Daily 5-minute diaphragmatic breathing and stress reduction."
    daily_tasks: List[DailyTask] = []
    clinician_reviewed: bool = False
    clinician_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
