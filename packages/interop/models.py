"""Normalized Internal Clinical Domain Models for Multi-EMR Interoperability.

Strict Isolation Boundary:
Zero provider-specific schema details (such as FHIR R4 raw bundles,
openEHR AQL responses, or Prisma HMS database rows) leak outside
the adapters. All consumers, services, and AI agents interact solely with
these clean, validated domain models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid


class ClinicalSourceSystem(str, Enum):
    """Originating clinical source repository."""
    SEVAHEALTH_LOCAL = "SEVAHEALTH_LOCAL"
    OPENEHR_EHRBASE = "OPENEHR_EHRBASE"
    BEZS_EMR_GQL = "BEZS_EMR_GQL"
    BEZS_HMS = "BEZS_HMS"


class ObservationCategory(str, Enum):
    VITAL_SIGN = "VITAL_SIGN"
    LABORATORY = "LABORATORY"
    LIFESTYLE = "LIFESTYLE"
    PHYSICAL_EXAM = "PHYSICAL_EXAM"
    SURVEY = "SURVEY"


class ConditionClinicalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RECURRENCE = "RECURRENCE"
    REMISSION = "REMISSION"
    RESOLVED = "RESOLVED"


class ConditionVerificationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PROVISIONAL = "PROVISIONAL"
    DIFFERENTIAL = "DIFFERENTIAL"
    REFUTED = "REFUTED"


class MedicationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    ON_HOLD = "ON_HOLD"


class EncounterClass(str, Enum):
    AMBULATORY = "AMBULATORY"
    VIRTUAL = "VIRTUAL"
    INPATIENT = "INPATIENT"
    FIELD_VISIT = "FIELD_VISIT"


class CarePlanStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    REVOKED = "REVOKED"


class ClinicalDocumentType(str, Enum):
    LAB_REPORT = "LAB_REPORT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    PRESCRIPTION = "PRESCRIPTION"
    INTAKE_ASSESSMENT = "INTAKE_ASSESSMENT"
    SOAP_REPORT = "SOAP_REPORT"
    CLINICAL_NOTE = "CLINICAL_NOTE"


# ==============================================================================
# NORMALIZED INTERNAL CLINICAL DOMAIN ENTITIES
# ==============================================================================

class NormalizedPatient(BaseModel):
    """Normalized master patient record unified across multiple clinical sources."""
    id: str = Field(description="Normalized internal patient identifier")
    national_id: Optional[str] = Field(default=None, description="ABHA ID or National identifier")
    source_system: ClinicalSourceSystem = Field(description="Originating system of record")
    source_patient_id: str = Field(description="Original ID in the provider system")
    name: str = Field(description="Full patient name")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: str = Field(description="MALE, FEMALE, OTHER, UNKNOWN")
    birth_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedObservation(BaseModel):
    """Standardized physiological or laboratory clinical observation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    source_system: ClinicalSourceSystem
    source_record_id: Optional[str] = None
    code: str = Field(description="Standardized code (e.g. LOINC: 8867-4, 8480-6, 4548-4)")
    display_name: str = Field(description="Human readable name e.g. Heart Rate, Systolic BP, HbA1c")
    category: ObservationCategory = ObservationCategory.VITAL_SIGN
    value: float = Field(description="Numeric measurement value")
    unit: str = Field(description="Standardized unit (e.g. mmHg, bpm, mg/dL, %)")
    reference_range: Optional[str] = Field(default=None, description="e.g. 70-99 mg/dL")
    interpretation: Optional[str] = Field(default=None, description="NORMAL, HIGH, CRITICAL_HIGH, LOW")
    effective_datetime: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="FINAL", description="FINAL | PRELIMINARY | AMENDED")
    device_info: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedCondition(BaseModel):
    """Standardized clinical diagnosis or medical condition."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    source_system: ClinicalSourceSystem
    source_record_id: Optional[str] = None
    code: str = Field(description="ICD-10 or SNOMED-CT code (e.g. E11.9, I10)")
    display_name: str = Field(description="Condition description e.g. Type 2 Diabetes Mellitus")
    clinical_status: ConditionClinicalStatus = ConditionClinicalStatus.ACTIVE
    verification_status: ConditionVerificationStatus = ConditionVerificationStatus.CONFIRMED
    severity: Optional[str] = Field(default="MODERATE", description="MILD | MODERATE | SEVERE")
    onset_date: Optional[str] = None
    recorded_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedMedication(BaseModel):
    """Standardized medication order or active therapy."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    source_system: ClinicalSourceSystem
    source_record_id: Optional[str] = None
    code: Optional[str] = Field(default=None, description="RxNorm or national formulary code")
    medication_name: str = Field(description="Medication trade or generic name")
    dosage_instruction: str = Field(description="e.g. 500 mg orally twice daily with meals")
    status: MedicationStatus = MedicationStatus.ACTIVE
    route: Optional[str] = Field(default="ORAL", description="ORAL | SUBCUTANEOUS | INHALATION")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    prescriber_name: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedEncounter(BaseModel):
    """Standardized clinical encounter or consultation episode."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    source_system: ClinicalSourceSystem
    source_record_id: Optional[str] = None
    encounter_class: EncounterClass = EncounterClass.AMBULATORY
    status: str = Field(default="COMPLETED", description="PLANNED | IN_PROGRESS | COMPLETED | CANCELLED")
    reason: Optional[str] = None
    soap_note: Optional[Dict[str, str]] = Field(
        default=None,
        description="Structured SOAP Note: {'subjective': ..., 'objective': ..., 'assessment': ..., 'plan': ...}"
    )
    period_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: Optional[datetime] = None
    provider_name: Optional[str] = None
    facility_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedCarePlan(BaseModel):
    """Standardized preventive or therapeutic care plan."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    source_system: ClinicalSourceSystem
    source_record_id: Optional[str] = None
    title: str
    status: CarePlanStatus = CarePlanStatus.ACTIVE
    intent: str = Field(default="PREVENTION", description="PREVENTION | MANAGEMENT | REHABILITATION")
    goals: List[Dict[str, Any]] = Field(default_factory=list)
    activities: List[Dict[str, Any]] = Field(default_factory=list)
    period_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedClinicalDocument(BaseModel):
    """Standardized clinical document (SOAP report, intake assessment, lab report)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    source_system: ClinicalSourceSystem
    source_record_id: Optional[str] = None
    document_type: ClinicalDocumentType
    title: str
    status: str = Field(default="FINAL", description="FINAL | PRELIMINARY | AMENDED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    author: Optional[str] = None
    content_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FederatedClinicalChart(BaseModel):
    """Comprehensive aggregated clinical chart unified across all integrated systems."""
    patient: Optional[NormalizedPatient] = None
    patient_id: str
    observations: List[NormalizedObservation] = Field(default_factory=list)
    conditions: List[NormalizedCondition] = Field(default_factory=list)
    medications: List[NormalizedMedication] = Field(default_factory=list)
    encounters: List[NormalizedEncounter] = Field(default_factory=list)
    care_plans: List[NormalizedCarePlan] = Field(default_factory=list)
    documents: List[NormalizedClinicalDocument] = Field(default_factory=list)
    source_systems_queried: List[ClinicalSourceSystem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
