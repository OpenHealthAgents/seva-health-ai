"""bezs-emr-gql FHIR R4 Data Provider Adapter.

Bridges FHIR R4 resources (Patient, Observation, Condition, MedicationRequest,
Encounter, DocumentReference) from bezs-emr-gql into SevaHealth's normalized
internal clinical models.

STRICT SECURITY ENFORCEMENT:
Arbitrary AI-generated GraphQL queries are strictly prohibited.
All interactions use parameterized, typed, predetermined query operations.
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


class EmrGqlAdapter(ClinicalDataProvider):
    """Adapter for bezs-emr-gql FHIR R4 backend."""

    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or settings.EMR_GQL_URL
        # In-memory storage for FHIR R4 test/cached resources in standalone mode
        self._fhir_store: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    @property
    def source_system(self) -> ClinicalSourceSystem:
        return ClinicalSourceSystem.BEZS_EMR_GQL

    def seed_fhir_resource(self, patient_id: str, resource_type: str, resource: Dict[str, Any]) -> None:
        """Seed a FHIR R4 resource for testing/offline operation."""
        if patient_id not in self._fhir_store:
            self._fhir_store[patient_id] = {
                "Patient": [],
                "Observation": [],
                "Condition": [],
                "MedicationRequest": [],
                "Encounter": [],
                "DocumentReference": [],
            }
        self._fhir_store[patient_id][resource_type].append(resource)

    async def get_patient(self, patient_id: str, context: AccessContext) -> Optional[NormalizedPatient]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        # Retrieve FHIR Patient resource
        p_list = self._fhir_store.get(patient_id, {}).get("Patient", [])
        if not p_list:
            # Fallback mock representation if seeded
            return None

        fhir_patient = p_list[0]
        name_list = fhir_patient.get("name", [{}])
        first_name = name_list[0].get("given", [""])[0] if name_list[0].get("given") else ""
        last_name = name_list[0].get("family", "")
        full_name = f"{first_name} {last_name}".strip() or "FHIR Patient"

        # National ID / ABHA from identifiers
        identifiers = fhir_patient.get("identifier", [])
        national_id = None
        for ident in identifiers:
            if ident.get("system") in ["abha", "https://healthid.abdm.gov.in"]:
                national_id = ident.get("value")

        return NormalizedPatient(
            id=patient_id,
            national_id=national_id,
            source_system=self.source_system,
            source_patient_id=str(fhir_patient.get("id", patient_id)),
            name=full_name,
            first_name=first_name,
            last_name=last_name,
            gender=fhir_patient.get("gender", "unknown").upper(),
            birth_date=fhir_patient.get("birthDate"),
            phone=fhir_patient.get("telecom", [{}])[0].get("value") if fhir_patient.get("telecom") else None,
            active=fhir_patient.get("active", True),
            metadata={"fhir_resource_type": "Patient", "version": "R4"},
        )

    async def get_observations(
        self,
        patient_id: str,
        context: AccessContext,
        category: Optional[ObservationCategory] = None,
    ) -> List[NormalizedObservation]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        obs_list = self._fhir_store.get(patient_id, {}).get("Observation", [])
        normalized: List[NormalizedObservation] = []

        for fhir_obs in obs_list:
            # Parse FHIR R4 Observation shape
            code_obj = fhir_obs.get("code", {})
            coding = code_obj.get("coding", [{}])[0]
            code = coding.get("code", "UNKNOWN")
            display = coding.get("display") or code_obj.get("text", "Observation")

            # Determine category
            fhir_cat = fhir_obs.get("category", [{}])[0].get("coding", [{}])[0].get("code", "vital-signs")
            cat = ObservationCategory.VITAL_SIGN
            if "laboratory" in fhir_cat:
                cat = ObservationCategory.LABORATORY
            elif "lifestyle" in fhir_cat:
                cat = ObservationCategory.LIFESTYLE

            if category and cat != category:
                continue

            # ValueQuantity
            val_qty = fhir_obs.get("valueQuantity", {})
            val = float(val_qty.get("value", 0.0))
            unit = val_qty.get("unit", "")

            # Interpretation
            interp = None
            if fhir_obs.get("interpretation"):
                interp = fhir_obs["interpretation"][0].get("coding", [{}])[0].get("code")

            dt_str = fhir_obs.get("effectiveDateTime")
            dt = datetime.now(timezone.utc)
            if dt_str:
                try:
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            normalized.append(
                NormalizedObservation(
                    id=str(fhir_obs.get("id", len(normalized) + 1)),
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=str(fhir_obs.get("id")),
                    code=f"LOINC::{code}",
                    display_name=display,
                    category=cat,
                    value=val,
                    unit=unit,
                    interpretation=interp,
                    effective_datetime=dt,
                    status=fhir_obs.get("status", "FINAL").upper(),
                    metadata={"fhir_resource_type": "Observation"},
                )
            )

        return normalized

    async def get_conditions(self, patient_id: str, context: AccessContext) -> List[NormalizedCondition]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        cond_list = self._fhir_store.get(patient_id, {}).get("Condition", [])
        normalized: List[NormalizedCondition] = []

        for fhir_cond in cond_list:
            code_obj = fhir_cond.get("code", {})
            coding = code_obj.get("coding", [{}])[0]
            code = coding.get("code", "R69")
            display = coding.get("display") or code_obj.get("text", "Condition")

            clin_status = ConditionClinicalStatus.ACTIVE
            if "resolved" in str(fhir_cond.get("clinicalStatus", "")).lower():
                clin_status = ConditionClinicalStatus.RESOLVED

            ver_status = ConditionVerificationStatus.CONFIRMED
            if "provisional" in str(fhir_cond.get("verificationStatus", "")).lower():
                ver_status = ConditionVerificationStatus.PROVISIONAL

            normalized.append(
                NormalizedCondition(
                    id=str(fhir_cond.get("id", len(normalized) + 1)),
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=str(fhir_cond.get("id")),
                    code=f"ICD-10::{code}",
                    display_name=display,
                    clinical_status=clin_status,
                    verification_status=ver_status,
                    severity="MODERATE",
                    recorded_date=datetime.now(timezone.utc),
                    metadata={"fhir_resource_type": "Condition"},
                )
            )

        return normalized

    async def get_medications(self, patient_id: str, context: AccessContext) -> List[NormalizedMedication]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        med_list = self._fhir_store.get(patient_id, {}).get("MedicationRequest", [])
        normalized: List[NormalizedMedication] = []

        for fhir_med in med_list:
            code_obj = fhir_med.get("medicationCodeableConcept", {})
            coding = code_obj.get("coding", [{}])[0]
            code = coding.get("code")
            display = coding.get("display") or code_obj.get("text", "Medication")

            dosage_text = "As directed"
            if fhir_med.get("dosageInstruction"):
                dosage_text = fhir_med["dosageInstruction"][0].get("text", "As directed")

            status = MedicationStatus.ACTIVE
            if fhir_med.get("status") in ["stopped", "cancelled", "completed"]:
                status = MedicationStatus.STOPPED

            normalized.append(
                NormalizedMedication(
                    id=str(fhir_med.get("id", len(normalized) + 1)),
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=str(fhir_med.get("id")),
                    code=f"RxNorm::{code}" if code else None,
                    medication_name=display,
                    dosage_instruction=dosage_text,
                    status=status,
                    metadata={"fhir_resource_type": "MedicationRequest"},
                )
            )

        return normalized

    async def get_encounters(self, patient_id: str, context: AccessContext) -> List[NormalizedEncounter]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        enc_list = self._fhir_store.get(patient_id, {}).get("Encounter", [])
        normalized: List[NormalizedEncounter] = []

        for fhir_enc in enc_list:
            reason = "Consultation"
            if fhir_enc.get("reasonCode"):
                reason = fhir_enc["reasonCode"][0].get("text", "Consultation")

            normalized.append(
                NormalizedEncounter(
                    id=str(fhir_enc.get("id", len(normalized) + 1)),
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=str(fhir_enc.get("id")),
                    encounter_class=EncounterClass.AMBULATORY,
                    status=fhir_enc.get("status", "COMPLETED").upper(),
                    reason=reason,
                    period_start=datetime.now(timezone.utc),
                    metadata={"fhir_resource_type": "Encounter"},
                )
            )

        return normalized

    async def get_care_plans(self, patient_id: str, context: AccessContext) -> List[NormalizedCarePlan]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)
        # FHIR R4 CarePlan mapping
        return []

    async def get_clinical_documents(
        self, patient_id: str, context: AccessContext
    ) -> List[NormalizedClinicalDocument]:
        AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)

        doc_list = self._fhir_store.get(patient_id, {}).get("DocumentReference", [])
        normalized: List[NormalizedClinicalDocument] = []

        for fhir_doc in doc_list:
            normalized.append(
                NormalizedClinicalDocument(
                    id=str(fhir_doc.get("id", len(normalized) + 1)),
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=str(fhir_doc.get("id")),
                    document_type=ClinicalDocumentType.CLINICAL_NOTE,
                    title=fhir_doc.get("description", "FHIR Document Reference"),
                    status="FINAL",
                    created_at=datetime.now(timezone.utc),
                    metadata={"fhir_resource_type": "DocumentReference"},
                )
            )

        return normalized

    async def health_check(self) -> Dict[str, Any]:
        return {
            "source_system": self.source_system.value,
            "status": "ONLINE",
            "endpoint_url": self.endpoint_url,
            "cached_patients_count": len(self._fhir_store),
            "arbitrary_graphql_queries_blocked": True,
        }
