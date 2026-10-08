"""Clinical Document Ingestion Subsystem - Data Models.

Defines schemas for:
- Document classification (LAB_REPORT, PRESCRIPTION, DISCHARGE_SUMMARY, etc.)
- 10-stage ingestion lifecycle
- Clinical entity extractions (Patient, Tests, Medications, Diagnoses, Provider, Facility, Dates)
- Mathematical confidence scoring ($0.0 - 1.0$)
- Provenance tracking (SHA-256, page, line, engine)
- Human review queue and correction tracking
- Committed clinical observations and legal records
"""

from datetime import datetime, timezone, date
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import uuid


class DocumentType(str, Enum):
    LAB_REPORT = "LAB_REPORT"
    PRESCRIPTION = "PRESCRIPTION"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    HEALTH_PACKAGE_REPORT = "HEALTH_PACKAGE_REPORT"
    MEDICAL_REPORT = "MEDICAL_REPORT"
    UNKNOWN = "UNKNOWN"


class IngestionStatus(str, Enum):
    UPLOADED = "UPLOADED"
    VALIDATING_FILE = "VALIDATING_FILE"
    CLASSIFYING = "CLASSIFYING"
    OCR_PROCESSING = "OCR_PROCESSING"
    EXTRACTING = "EXTRACTING"
    NORMALIZING = "NORMALIZING"
    VALIDATING = "VALIDATING"
    MAPPING_CLINICAL = "MAPPING_CLINICAL"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    COMMITTED_TO_CLINICAL_RECORD = "COMMITTED_TO_CLINICAL_RECORD"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class FieldReviewStatus(str, Enum):
    AUTO_ACCEPTED = "AUTO_ACCEPTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REVIEWER_APPROVED = "REVIEWER_APPROVED"
    REVIEWER_CORRECTED = "REVIEWER_CORRECTED"
    REVIEWER_REJECTED = "REVIEWER_REJECTED"


class ProvenanceRecord(BaseModel):
    """Immutable audit trail of where and how a clinical entity was extracted."""
    source_document_id: str
    file_sha256: str
    page_number: int = 1
    line_number: Optional[int] = None
    bounding_box: Optional[Dict[str, float]] = None  # {x0, y0, x1, y1}
    raw_text_snippet: str
    extractor_engine: str = "SevaHealth-Clinical-OCR-Extractor-v2"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExtractedPatientInfo(BaseModel):
    """Patient identification entities extracted from the clinical document."""
    patient_name: Optional[str] = None
    patient_name_confidence: float = 0.0
    abha_id: Optional[str] = None
    abha_id_confidence: float = 0.0
    age: Optional[int] = None
    age_confidence: float = 0.0
    gender: Optional[str] = None
    gender_confidence: float = 0.0
    mrn_or_patient_id: Optional[str] = None
    mrn_confidence: float = 0.0
    provenance: Optional[ProvenanceRecord] = None


class ExtractedLabTest(BaseModel):
    """Structured clinical laboratory or vital measurement."""
    id: str = Field(default_factory=lambda: f"test-{uuid.uuid4().hex[:8]}")
    test_name: str
    canonical_name: Optional[str] = None
    raw_value: str
    numeric_value: Optional[float] = None
    raw_unit: Optional[str] = None
    normalized_unit: Optional[str] = None
    reference_range_raw: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    interpretation: Optional[str] = None  # NORMAL | HIGH | LOW | CRITICAL
    loinc_code: Optional[str] = None
    loinc_display: Optional[str] = None
    confidence: float = 0.0
    is_valid_physiological: bool = True
    validation_flags: List[str] = Field(default_factory=list)
    review_status: FieldReviewStatus = FieldReviewStatus.PENDING_REVIEW
    reviewed_value: Optional[Union[float, str]] = None
    reviewed_unit: Optional[str] = None
    reviewer_comments: Optional[str] = None
    provenance: Optional[ProvenanceRecord] = None


class ExtractedMedication(BaseModel):
    """Medication order or prescription item."""
    id: str = Field(default_factory=lambda: f"med-{uuid.uuid4().hex[:8]}")
    drug_name: str
    canonical_name: Optional[str] = None
    dose_amount: Optional[str] = None
    dose_unit: Optional[str] = None
    route: Optional[str] = "ORAL"
    frequency: Optional[str] = None        # e.g., "OD", "BD", "TDS", "1-0-1"
    duration: Optional[str] = None         # e.g., "30 days"
    instructions: Optional[str] = None     # e.g., "After meals"
    rxnorm_code: Optional[str] = None
    atc_code: Optional[str] = None
    confidence: float = 0.0
    review_status: FieldReviewStatus = FieldReviewStatus.PENDING_REVIEW
    provenance: Optional[ProvenanceRecord] = None


class ExtractedDiagnosis(BaseModel):
    """Diagnosis or clinical condition identified in reports/summaries."""
    id: str = Field(default_factory=lambda: f"diag-{uuid.uuid4().hex[:8]}")
    diagnosis_name: str
    diagnosis_type: str = "PRIMARY"        # PRIMARY | SECONDARY | PROVISIONAL
    icd10_code: Optional[str] = None
    snomed_ct_code: Optional[str] = None
    confidence: float = 0.0
    review_status: FieldReviewStatus = FieldReviewStatus.PENDING_REVIEW
    provenance: Optional[ProvenanceRecord] = None


class ExtractedProvider(BaseModel):
    """Treating clinician or laboratory pathologist."""
    doctor_name: Optional[str] = None
    registration_number: Optional[str] = None
    specialty: Optional[str] = None
    qualification: Optional[str] = None
    confidence: float = 0.0
    provenance: Optional[ProvenanceRecord] = None


class ExtractedFacility(BaseModel):
    """Hospital, diagnostic centre, or laboratory facility."""
    facility_name: Optional[str] = None
    facility_type: Optional[str] = None   # PHC | CHC | DISTRICT_HOSPITAL | DIAGNOSTIC_LAB
    address: Optional[str] = None
    accreditation: Optional[str] = None   # NABL | NABH
    confidence: float = 0.0
    provenance: Optional[ProvenanceRecord] = None


class ExtractedDates(BaseModel):
    """All temporal anchors found in the clinical document."""
    report_date: Optional[str] = None
    specimen_collection_date: Optional[str] = None
    prescription_date: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    confidence: float = 0.0
    provenance: Optional[ProvenanceRecord] = None


class ClinicalExtractionBundle(BaseModel):
    """Complete collection of extracted clinical entities from one document."""
    patient: ExtractedPatientInfo = Field(default_factory=ExtractedPatientInfo)
    dates: ExtractedDates = Field(default_factory=ExtractedDates)
    provider: ExtractedProvider = Field(default_factory=ExtractedProvider)
    facility: ExtractedFacility = Field(default_factory=ExtractedFacility)
    tests: List[ExtractedLabTest] = Field(default_factory=list)
    medications: List[ExtractedMedication] = Field(default_factory=list)
    diagnoses: List[ExtractedDiagnosis] = Field(default_factory=list)
    summary_notes: Optional[str] = None
    mean_confidence: float = 0.0
    low_confidence_fields_count: int = 0


class HumanReviewCorrection(BaseModel):
    """Clinician / reviewer action on an extracted field or document."""
    action: str  # APPROVE | CORRECT | REJECT
    target_category: str  # TEST | MEDICATION | DIAGNOSIS | PATIENT | DATES
    target_id: str
    corrected_value: Optional[Any] = None
    corrected_unit: Optional[str] = None
    corrected_interpretation: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewer_id: str
    reviewer_name: str


class DocumentMetadata(BaseModel):
    """Preserved original document metadata."""
    document_id: str
    citizen_id: str
    title: str
    filename: str
    content_type: str
    size_bytes: int
    sha256_hash: str
    storage_path: str
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_quarantined: bool = False
    virus_scan_passed: bool = True
    virus_scan_details: str = "Clean"


class DocumentIngestionJob(BaseModel):
    """State machine tracking document ingestion through all 10 pipeline stages."""
    job_id: str = Field(default_factory=lambda: f"job-{uuid.uuid4().hex[:10]}")
    document_id: str
    citizen_id: str
    status: IngestionStatus = IngestionStatus.UPLOADED
    document_type: DocumentType = DocumentType.UNKNOWN
    classification_confidence: float = 0.0
    ocr_pages_count: int = 0
    raw_text: str = ""
    extractions: ClinicalExtractionBundle = Field(default_factory=ClinicalExtractionBundle)
    overall_confidence: float = 0.0
    requires_human_review: bool = True
    human_review_reasons: List[str] = Field(default_factory=list)
    pipeline_stage_timings: Dict[str, float] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    committed_observation_ids: List[str] = Field(default_factory=list)
    committed_legal_record_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
