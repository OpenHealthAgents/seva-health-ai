"""Domain & API Models for Mobile-First Health Worker Application."""

from datetime import datetime, timezone, date
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid


class OfflineDraftType(str, Enum):
    CITIZEN_REGISTRATION = "CITIZEN_REGISTRATION"
    CONSENT = "CONSENT"
    SCREENING = "SCREENING"
    REFERRAL = "REFERRAL"
    FOLLOWUP = "FOLLOWUP"


class SyncStatus(str, Enum):
    PENDING = "PENDING"
    SYNCED = "SYNCED"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    ALREADY_PROCESSED = "ALREADY_PROCESSED"
    FAILED = "FAILED"


class CommunityProgram(BaseModel):
    id: str
    name: str
    state: str = "Karnataka"
    district: str = "Mysuru"
    communities: List[str] = Field(default_factory=list)
    description: str
    target_domains: List[str] = Field(default_factory=list)
    active_workflows: List[str] = Field(default_factory=list)


class OfflineSyncItem(BaseModel):
    draft_id: str
    type: OfflineDraftType
    client_timestamp: datetime
    idempotency_key: str
    payload: Dict[str, Any]
    client_version: int = 1


class BatchSyncRequest(BaseModel):
    device_id: str = "mobile-android-asha-device-01"
    worker_id: str
    app_version: str = "1.0.0"
    drafts: List[OfflineSyncItem]


class SyncItemResult(BaseModel):
    draft_id: str
    type: OfflineDraftType
    status: SyncStatus
    server_id: Optional[str] = None
    client_version: int = 1
    server_version: int = 1
    message: str = "Successfully synchronized."
    conflict_details: Optional[Dict[str, Any]] = None
    resolved_data: Optional[Dict[str, Any]] = None


class BatchSyncResponse(BaseModel):
    device_id: str
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_submitted: int
    synced_count: int
    conflicts_count: int
    failed_count: int
    results: List[SyncItemResult]


class ReferralCreatePayload(BaseModel):
    citizen_id: str
    facility_name: str = "Mysuru District Hospital - NCD Special Clinic"
    facility_type: str = "DISTRICT_HOSPITAL"  # PHC | CHC | DISTRICT_HOSPITAL
    urgency: str = "PRIORITY"               # ROUTINE | PRIORITY | EMERGENT
    reason: str
    provisional_diagnosis: Optional[str] = None
    clinical_notes: Optional[str] = None
    transport_assistance_needed: bool = False


class ReferralRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    referral_slip_id: str
    citizen_id: str
    referring_worker_id: str
    facility_name: str
    facility_type: str
    urgency: str
    reason: str
    provisional_diagnosis: Optional[str] = None
    clinical_notes: Optional[str] = None
    transport_assistance_needed: bool = False
    status: str = "ACTIVE"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FollowUpCreatePayload(BaseModel):
    citizen_id: str
    scheduled_date: str                   # YYYY-MM-DD
    purpose: str = "Repeat Vitals & Dietary Compliance Review"
    contact_mode: str = "HOME_VISIT"      # HOME_VISIT | ANGANWADI_CAMP | PHC_FACILITY | PHONE_CALL
    notes: Optional[str] = None


class FollowUpRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    citizen_id: str
    assigned_worker_id: str
    scheduled_date: str
    purpose: str
    contact_mode: str
    notes: Optional[str] = None
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NextActionRecommendation(BaseModel):
    urgency_tier: str                     # RED | AMBER | GREEN
    headline: str
    action_items: List[str]
    clinical_rationale: str
    referral_recommended: bool = False
    suggested_referral_facility: Optional[str] = None
    followup_days_suggested: int = 14
    counseling_points: List[str] = Field(default_factory=list)


class HealthWorkerDashboard(BaseModel):
    worker_id: str
    worker_name: str
    program_name: str
    assigned_jurisdiction: str
    screenings_today_count: int
    high_risk_flagged_count: int
    pending_followups_count: int
    recent_citizens: List[Dict[str, Any]] = Field(default_factory=list)
