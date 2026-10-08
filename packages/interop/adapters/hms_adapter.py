"""bezs-hms Clinical Data Provider Adapter.

Bridges Hospital Management System (HMS) Intakes (conversations & clinical
assessment reports) and Consultations (virtual sessions, SOAP notes, and
extracted orders) into SevaHealth's normalized internal clinical models.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import structlog

from packages.config.settings import settings
from packages.interop.base import ClinicalDataProvider, AccessContext
from packages.interop.security import AntiArbitraryQueryGuard
from packages.interop.models import (
    ClinicalSourceSystem,
    NormalizedPatient,
    NormalizedObservation,
    NormalizedCondition,
    NormalizedMedication,
    NormalizedEncounter,
    NormalizedCarePlan,
    NormalizedClinicalDocument,
    ObservationCategory,
    ConditionClinicalStatus,
    ConditionVerificationStatus,
    MedicationStatus,
    EncounterClass,
    ClinicalDocumentType,
)

logger = structlog.get_logger(__name__)


class HmsAdapter(ClinicalDataProvider):
    """Adapter bridging bezs-hms Intakes and Consultations to normalized clinical domain objects."""

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or settings.HMS_API_URL
        # In-memory store for HMS Intakes and Consultations
        self._intakes: Dict[str, List[Dict[str, Any]]] = {}        # patient_id -> list of Intakes
        self._consultations: Dict[str, List[Dict[str, Any]]] = {}  # patient_id -> list of Consultations

    @property
    def source_system(self) -> ClinicalSourceSystem:
        return ClinicalSourceSystem.BEZS_HMS

    def seed_intake(self, patient_id: str, intake_record: Dict[str, Any]) -> None:
        """Seed an HMS Intake record for testing or mock integration."""
        if patient_id not in self._intakes:
            self._intakes[patient_id] = []
        self._intakes[patient_id].append(intake_record)

    def seed_consultation(self, patient_id: str, consultation_record: Dict[str, Any]) -> None:
        """Seed an HMS Consultation record with SOAP note and extractions."""
        if patient_id not in self._consultations:
            self._consultations[patient_id] = []
        self._consultations[patient_id].append(consultation_record)

    async def get_patient(self, patient_id: str, context: AccessContext) -> Optional[NormalizedPatient]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        # HMS references Better Auth user_id and patient_fhir_id
        return NormalizedPatient(
            id=patient_id,
            source_system=self.source_system,
            source_patient_id=patient_id,
            name=f"HMS Patient {patient_id[:8]}",
            gender="UNKNOWN",
            active=True,
            metadata={"hms_api_url": self.api_url},
        )

    async def get_observations(
        self,
        patient_id: str,
        context: AccessContext,
        category: Optional[ObservationCategory] = None,
    ) -> List[NormalizedObservation]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        observations: List[NormalizedObservation] = []
        consultations = self._consultations.get(patient_id, [])

        for c in consultations:
            raw_obs_list = c.get("observations") or []
            for obs in raw_obs_list:
                cat = ObservationCategory.VITAL_SIGN
                if "lab" in obs.get("code", "").lower():
                    cat = ObservationCategory.LABORATORY

                if category and cat != category:
                    continue

                observations.append(
                    NormalizedObservation(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=str(c.get("id")),
                        code=f"HMS::{obs.get('code', 'OBS')}",
                        display_name=obs.get("display", "Clinical Observation"),
                        category=cat,
                        value=float(obs.get("value", 0.0)),
                        unit=obs.get("unit", ""),
                        interpretation=obs.get("interpretation"),
                        effective_datetime=datetime.now(timezone.utc),
                        status="FINAL",
                        metadata={"consultation_id": c.get("id"), "room_id": c.get("room_id")},
                    )
                )

        return observations

    async def get_conditions(self, patient_id: str, context: AccessContext) -> List[NormalizedCondition]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        conditions: List[NormalizedCondition] = []

        # 1. From Intake Reports (AI differential diagnoses / risk findings)
        intakes = self._intakes.get(patient_id, [])
        for intake in intakes:
            report = intake.get("report") or {}
            diff_diag = report.get("differential_diagnosis", [])
            for diag in diff_diag:
                conditions.append(
                    NormalizedCondition(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=str(intake.get("id")),
                        code=f"HMS-INTAKE::{diag.get('code', 'DIFF')}",
                        display_name=diag.get("condition", "Intake Suspected Condition"),
                        clinical_status=ConditionClinicalStatus.ACTIVE,
                        verification_status=ConditionVerificationStatus.PROVISIONAL,
                        severity=report.get("risk_level", "MODERATE"),
                        recorded_date=datetime.now(timezone.utc),
                        notes=f"Intake mode: {intake.get('mode', 'TEXT')}",
                    )
                )

        # 2. From Doctor Consultations (Approved post-consultation conditions)
        consultations = self._consultations.get(patient_id, [])
        for c in consultations:
            cond_list = c.get("conditions") or []
            for cond in cond_list:
                conditions.append(
                    NormalizedCondition(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=str(c.get("id")),
                        code=f"HMS-CONSULT::{cond.get('code', 'DIAG')}",
                        display_name=cond.get("display", "Consultation Diagnosis"),
                        clinical_status=ConditionClinicalStatus.ACTIVE,
                        verification_status=ConditionVerificationStatus.CONFIRMED if c.get("published_at") else ConditionVerificationStatus.PROVISIONAL,
                        severity="MODERATE",
                        recorded_date=datetime.now(timezone.utc),
                        notes=f"Approved by Doctor: {c.get('published_by', 'Pending')}",
                    )
                )

        return conditions

    async def get_medications(self, patient_id: str, context: AccessContext) -> List[NormalizedMedication]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        medications: List[NormalizedMedication] = []
        consultations = self._consultations.get(patient_id, [])

        for c in consultations:
            med_reqs = c.get("medication_requests") or []
            for m in med_reqs:
                medications.append(
                    NormalizedMedication(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=str(c.get("id")),
                        medication_name=m.get("medication_name", "Prescribed Medication"),
                        dosage_instruction=m.get("dosage_instruction", "As directed by physician"),
                        status=MedicationStatus.ACTIVE,
                        prescriber_name=c.get("published_by", "HMS Physician"),
                        metadata={"consultation_id": c.get("id")},
                    )
                )

        return medications

    async def get_encounters(self, patient_id: str, context: AccessContext) -> List[NormalizedEncounter]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        encounters: List[NormalizedEncounter] = []
        consultations = self._consultations.get(patient_id, [])

        for c in consultations:
            soap = c.get("soap_note") or {}
            encounters.append(
                NormalizedEncounter(
                    id=f"hms_consult_{c.get('id')}",
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=str(c.get("id")),
                    encounter_class=EncounterClass.VIRTUAL,
                    status=c.get("status", "COMPLETED"),
                    reason="Virtual Doctor Video Consultation",
                    soap_note={
                        "subjective": soap.get("subjective", ""),
                        "objective": soap.get("objective", ""),
                        "assessment": soap.get("assessment", ""),
                        "plan": soap.get("plan", ""),
                    } if soap else None,
                    period_start=datetime.now(timezone.utc),
                    provider_name=c.get("published_by", "Doctor"),
                    metadata={
                        "room_id": c.get("room_id"),
                        "published_at": str(c.get("published_at")) if c.get("published_at") else None,
                    },
                )
            )

        return encounters

    async def get_care_plans(self, patient_id: str, context: AccessContext) -> List[NormalizedCarePlan]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)
        # Service requests / follow-up plan from consultations can map here if needed
        return []

    async def get_clinical_documents(
        self, patient_id: str, context: AccessContext
    ) -> List[NormalizedClinicalDocument]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        documents: List[NormalizedClinicalDocument] = []

        # 1. Intakes -> INTAKE_ASSESSMENT
        intakes = self._intakes.get(patient_id, [])
        for intake in intakes:
            documents.append(
                NormalizedClinicalDocument(
                    id=f"hms_intake_{intake.get('id')}",
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=str(intake.get("id")),
                    document_type=ClinicalDocumentType.INTAKE_ASSESSMENT,
                    title=f"Pre-Consultation Intake Report ({intake.get('mode', 'TEXT')})",
                    status="FINAL" if intake.get("status") == "COMPLETED" else "PRELIMINARY",
                    created_at=datetime.now(timezone.utc),
                    content_text=str(intake.get("report")),
                    structured_data={
                        "conversation": intake.get("conversation"),
                        "report": intake.get("report"),
                        "mode": intake.get("mode"),
                    },
                )
            )

        # 2. Consultations -> SOAP_REPORT
        consultations = self._consultations.get(patient_id, [])
        for c in consultations:
            full_rep = c.get("full_report")
            soap = c.get("soap_note")
            documents.append(
                NormalizedClinicalDocument(
                    id=f"hms_soap_{c.get('id')}",
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=str(c.get("id")),
                    document_type=ClinicalDocumentType.SOAP_REPORT,
                    title="Virtual Consultation SOAP Report",
                    status="FINAL" if c.get("published_at") else "PRELIMINARY",
                    created_at=datetime.now(timezone.utc),
                    author=c.get("published_by", "Doctor"),
                    structured_data={"soap_note": soap, "full_report": full_rep},
                )
            )

        return documents

    async def health_check(self) -> Dict[str, Any]:
        return {
            "source_system": self.source_system.value,
            "status": "ONLINE",
            "api_url": self.api_url,
            "intakes_count": sum(len(v) for v in self._intakes.values()),
            "consultations_count": sum(len(v) for v in self._consultations.values()),
        }
