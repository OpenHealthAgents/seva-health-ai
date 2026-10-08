from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import uuid

from packages.types.enums import (
    UserRole,
    Gender,
    RiskTier,
    TrajectoryTrend,
    TriageUrgency,
    ClinicianReviewStatus,
    InterventionPillar,
    AuditAction,
)


class ProvenanceRecord(BaseModel):
    """Forensic clinical provenance tracking device, operator, and method."""
    recorder_id: str
    recorder_role: UserRole
    device_model: Optional[str] = None
    device_id: Optional[str] = None
    capture_method: str = "DIRECT_SENSOR"  # DIRECT_SENSOR | CLINICIAN_ENTERED | PATIENT_REPORTED
    facility_code: Optional[str] = None


# 1. Organization
class Organization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # STATE_HEALTH_MISSION | DISTRICT_HEALTH_OFFICE | PHC | CHC
    jurisdiction: str  # e.g., "Karnataka", "Mysuru District", "Ward 12"
    parent_organization_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 2. CareTeam
class CareTeamMember(BaseModel):
    user_id: str
    role: UserRole
    name: str
    phone: Optional[str] = None


class CareTeam(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    name: str
    members: List[CareTeamMember] = []
    jurisdiction: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 3. Patient
class Patient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    abha_id: Optional[str] = None
    user_id: Optional[str] = None
    primary_care_team_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 4. Profile
class Profile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    first_name: str
    last_name: str
    birth_date: date
    gender: Gender
    phone: str
    email: Optional[str] = None
    state: str = "Karnataka"
    district: str = "Mysuru"
    sub_district: str = "Nanjangud"
    village_or_ward: str = "Ward 4"
    primary_language: str = "en"
    socioeconomic_tier: Optional[str] = "BPL"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 5. FamilyHistory
class FamilyHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    relative_relationship: str  # FATHER | MOTHER | SIBLING | MATERNAL_GRANDPARENT
    condition_code: str         # DIABETES_MELLITUS_TYPE_2 | HYPERTENSION | CAD
    condition_name: str
    age_at_onset: Optional[int] = None
    is_deceased: bool = False
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 6. LifestyleProfile
class LifestyleProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    tobacco_use: str  # NEVER | FORMER | CURRENT_SMOKER | CHEWING_TOBACCO
    alcohol_use: str  # NONE | OCCASIONAL | REGULAR | HEAVY
    dietary_pattern: str  # BALANCED | HIGH_CARB_HIGH_SALT | HIGH_PROCESSED
    physical_activity_level: str  # SEDENTARY | MODERATE_150_MIN_WK | VIGOROUS
    sleep_hours_per_night: float = Field(ge=0.0, le=24.0)
    perceived_stress_level: str = "MODERATE"  # LOW | MODERATE | SEVERE
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 7. RiskFactor
class RiskFactor(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    domain: str  # DIABETES | HYPERTENSION | CARDIOVASCULAR | METABOLIC | CKD | FATTY_LIVER
    name: str    # e.g., IMPAIRED_FASTING_GLYCEMIA, CENTRAL_VISCERAL_ADIPOSITY
    severity: str = "MODERATE"  # MILD | MODERATE | HIGH | CRITICAL
    identified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


# --- CLINICAL MEASUREMENT BASE CLASS ---
class ClinicalMeasurementBase(BaseModel):
    """Enforces strict clinical data standards:
    - Must have patient_id
    - Must have numeric/structured value
    - Must have unit (NEVER missing)
    - Must have measurement_timestamp (NEVER missing)
    - Must have source
    - Must have provenance
    - Must have confidence/quality score (0.0 to 1.0)
    - Never overwritten; append-only longitudinal history.
    """
    patient_id: str
    value: float
    unit: str
    measurement_timestamp: datetime
    source: str
    provenance: ProvenanceRecord
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Clinical measurement cannot be stored without a valid clinical unit.")
        return v.strip()

    @field_validator("measurement_timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        if not v:
            raise ValueError("Clinical measurement cannot be stored without an explicit measurement timestamp.")
        return v


# 8. VitalSign (Clinical Measurement)
class VitalSign(ClinicalMeasurementBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    clinical_type: str  # SYSTOLIC_BP | DIASTOLIC_BP | HEART_RATE | BMI | WAIST_CIRCUMFERENCE | RESPIRATORY_RATE | SPO2
    is_flagged_abnormal: bool = False
    notes: Optional[str] = None


# 9. LabResult (Clinical Measurement)
class LabResult(ClinicalMeasurementBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    test_name: str      # FASTING_BLOOD_GLUCOSE | HBA1C | TOTAL_CHOLESTEROL | TRIGLYCERIDES | HDL | LDL | SERUM_CREATININE
    loinc_code: str     # LOINC taxonomy code
    reference_range: str
    interpretation: str = "NORMAL"  # NORMAL | BORDERLINE | ELEVATED | CRITICAL


# 10. Medication
class Medication(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    drug_name: str
    dosage: str
    frequency: str
    indication: str
    prescribed_by: str
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True


# 11. MedicationAdherence
class MedicationAdherence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    medication_id: str
    scheduled_date: date
    taken: bool
    reported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason_skipped: Optional[str] = None


# 12. Screening
class Screening(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    screening_type: str  # NCD_COMPREHENSIVE_CBAC | IDRS_DIABETES_RISK | FIELD_CAMP_HYPERTENSION
    administered_by: str
    administrator_role: UserRole
    location: str
    screened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 13. ScreeningResult
class ScreeningResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    screening_id: str
    patient_id: str
    cbac_score: Optional[int] = None
    idrs_score: Optional[int] = None
    needs_immediate_referral: bool = False
    summary_findings: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 14. RiskAssessment
class RiskAssessment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    screening_id: Optional[str] = None
    overall_score: float = Field(ge=0.0, le=1.0)
    overall_tier: RiskTier
    domain_scores: Dict[str, float] = {}  # e.g., {"diabetes": 0.74, "hypertension": 0.62}
    clinical_safety_disclaimer: str = (
        "CLINICAL REVIEW RECOMMENDED: This assessment is an AI-assisted preventive health "
        "screening tool based on population guidelines. It does NOT constitute a medical diagnosis."
    )
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 15. RiskFactorContribution
class RiskFactorContribution(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    risk_assessment_id: str
    patient_id: str
    factor_name: str
    factor_category: str  # BIOMETRIC | LIFESTYLE | DEMOGRAPHIC
    observed_value: str
    target_value: str
    relative_weight: float
    is_protective: bool = False
    evidence_guideline: str


# 16. RiskTrajectory
class RiskTrajectory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    assessment_ids: List[str] = []
    historical_scores: List[Dict[str, Any]] = []
    trend: TrajectoryTrend
    rate_of_change: float = 0.0
    projected_tier_6m: RiskTier
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 17. InterventionPlan
class InterventionPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    risk_assessment_id: str
    title: str
    primary_domain: str
    duration_days: int = 30
    start_date: date
    end_date: date
    adherence_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 18. Intervention
class Intervention(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str
    pillar: InterventionPillar
    title: str
    prescription_text: str
    frequency: str
    target_metric: str


# 19. Goal
class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    plan_id: str
    metric_name: str  # e.g., SYSTOLIC_BP, DAILY_STEPS, HBA1C
    baseline_value: float
    target_value: float
    target_date: date
    status: str = "IN_PROGRESS"  # IN_PROGRESS | ACHIEVED | MISSED


# 20. CheckIn
class CheckIn(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    plan_id: str
    check_in_date: date
    tasks_completed_count: int = 0
    tasks_total_count: int = 0
    subjective_wellbeing: str = "GOOD"  # GOOD | NEUTRAL | STRUGGLING
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 21. WearableConnection
class WearableConnection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    device_brand: str  # Noise | Fire-Boltt | Apple | Fitbit | Garmin
    device_model: str
    connection_status: str = "CONNECTED"  # CONNECTED | SYNCING | DISCONNECTED
    last_synced_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 22. WearableObservation (Clinical Measurement)
class WearableObservation(ClinicalMeasurementBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_connection_id: str
    metric_type: str  # RESTING_HEART_RATE | HRV_RMSSD | DAILY_STEPS | SLEEP_DURATION_MINUTES
    rolling_7d_baseline: Optional[float] = None
    baseline_deviation_sigma: Optional[float] = None


# 23. ClinicalEncounter
class ClinicalEncounter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    clinician_id: str
    encounter_type: str  # PREVENTIVE_HEALTH_CAMP | PHC_OPD_CONSULTATION | TELEMEDICINE_TRIAGE
    reason_for_visit: str
    soap_subjective: str
    soap_objective: str
    soap_assessment: str
    soap_plan: str
    status: str = "COMPLETED"  # COMPLETED | IN_PROGRESS | CANCELLED
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None


# 24. CarePlan
class CarePlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    care_team_id: Optional[str] = None
    lead_clinician_id: Optional[str] = None
    title: str
    status: str = "ACTIVE"  # ACTIVE | COMPLETED | SUSPENDED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 25. Referral
class Referral(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    referring_worker_id: str
    referred_to_facility: str
    urgency: TriageUrgency = TriageUrgency.ROUTINE
    clinical_reason: str
    status: str = "PENDING"  # PENDING | ACCEPTED | COMPLETED | DECLINED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


# 26. Alert
class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    urgency: TriageUrgency = TriageUrgency.PRIORITY
    alert_type: str  # CRITICAL_HYPERTENSIVE_SPIKE | GLYCEMIC_DETERIORATION | ADHERENCE_DROP
    message: str
    clinical_rule_triggered: str
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 27. Notification
class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recipient_user_id: str
    patient_id: Optional[str] = None
    channel: str = "IN_APP"  # PUSH | SMS | WHATSAPP | IN_APP
    title: str
    body: str
    is_read: bool = False
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 28. Consent
class Consent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    grantee_id: str
    grantee_role: UserRole
    purpose: str = "CARE_DELIVERY"  # CARE_DELIVERY | RESEARCH | POPULATION_HEALTH
    scope_data_types: List[str] = ["VITALS", "LABS", "WEARABLES", "RISK_ASSESSMENTS"]
    status: str = "ACTIVE"          # ACTIVE | REVOKED | EXPIRED
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime
    revoked_at: Optional[datetime] = None

    def is_currently_valid(self) -> bool:
        if self.status != "ACTIVE":
            return False
        now = datetime.now(timezone.utc)
        return self.valid_from <= now <= self.valid_until


# 29. Document
class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    file_name: str
    file_type: str
    storage_path: str
    file_size_bytes: int
    sha256_hash: str
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 30. DocumentReference
class DocumentReference(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    patient_id: str
    doc_type: str  # DIAGNOSTIC_LAB_REPORT | CLINICAL_DISCHARGE_SUMMARY | PRESCRIPTION_SLIP
    clinical_summary: Optional[str] = None
    parsed_entities_json: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 31. AuditEvent
class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    actor_id: str
    actor_role: UserRole
    action: AuditAction
    resource_type: str
    resource_id: str
    patient_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
