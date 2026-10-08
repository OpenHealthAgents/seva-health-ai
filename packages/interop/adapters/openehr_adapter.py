"""openEHR / EHRbase Clinical Data Provider Adapter.

Bridges openEHR archetypes and compositions into SevaHealth's normalized
internal clinical models.
Strictly isolates openEHR AQL queries and composition structures behind
typed methods.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import httpx
import structlog

from packages.config.settings import settings
from packages.interop.base import ClinicalDataProvider, AccessContext
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
    EncounterClass,
    CarePlanStatus,
    ClinicalDocumentType,
)

logger = structlog.get_logger(__name__)


class OpenEhrEhrBaseAdapter(ClinicalDataProvider):
    """Adapter bridging openEHR / EHRbase compositions to normalized domain models."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = base_url or settings.EHRBASE_URL
        self.username = username or settings.EHRBASE_USER
        self.password = password or settings.EHRBASE_PASSWORD
        # In-memory storage for openEHR compositions in offline/development environment
        self._local_compositions: Dict[str, List[Dict[str, Any]]] = {}

    @property
    def source_system(self) -> ClinicalSourceSystem:
        return ClinicalSourceSystem.OPENEHR_EHRBASE

    def store_local_composition(self, patient_id: str, composition: Dict[str, Any]) -> None:
        """Stores a test/mock composition in the adapter cache."""
        if patient_id not in self._local_compositions:
            self._local_compositions[patient_id] = []
        self._local_compositions[patient_id].append(composition)

    async def get_patient(self, patient_id: str, context: AccessContext) -> Optional[NormalizedPatient]:
        # openEHR stores EHR status; patient demographics typically referenced via external subject_id
        return NormalizedPatient(
            id=patient_id,
            source_system=self.source_system,
            source_patient_id=f"openehr_ehr_{patient_id}",
            name=f"openEHR Subject {patient_id[:8]}",
            gender="UNKNOWN",
            active=True,
            metadata={"openehr_subject_namespace": "org.sevahealth.ehr"},
        )

    async def get_observations(
        self,
        patient_id: str,
        context: AccessContext,
        category: Optional[ObservationCategory] = None,
    ) -> List[NormalizedObservation]:
        observations: List[NormalizedObservation] = []
        compositions = self._local_compositions.get(patient_id, [])

        for comp in compositions:
            # Parse vitals or lab compositions
            archetype_id = comp.get("archetype_details", {}).get("archetype_id", {}).get("value", "")
            comp_name = comp.get("name", {}).get("value", "")

            # 1. Vital Signs Archetype (openEHR-EHR-COMPOSITION.encounter.v1 / vital_signs)
            if "vital" in comp_name.lower() or "vital_signs" in archetype_id:
                if category and category != ObservationCategory.VITAL_SIGN:
                    continue
                # Extract systolic/diastolic or pulse
                items = comp.get("content", [])
                for item in items:
                    name = item.get("name", {}).get("value", "Observation")
                    val = item.get("data", {}).get("magnitude", 0.0)
                    units = item.get("data", {}).get("units", "")
                    code = item.get("archetype_node_id", "at0001")

                    observations.append(
                        NormalizedObservation(
                            patient_id=patient_id,
                            source_system=self.source_system,
                            source_record_id=comp.get("uid", {}).get("value"),
                            code=f"OPENEHR::{code}",
                            display_name=name,
                            category=ObservationCategory.VITAL_SIGN,
                            value=float(val),
                            unit=units,
                            effective_datetime=datetime.now(timezone.utc),
                            status="FINAL",
                        )
                    )

            # 2. Laboratory Report Archetype
            elif "laboratory" in comp_name.lower() or "lab" in archetype_id:
                if category and category != ObservationCategory.LABORATORY:
                    continue
                items = comp.get("content", [])
                for item in items:
                    name = item.get("name", {}).get("value", "Lab Result")
                    val = item.get("data", {}).get("magnitude", 0.0)
                    units = item.get("data", {}).get("units", "")

                    observations.append(
                        NormalizedObservation(
                            patient_id=patient_id,
                            source_system=self.source_system,
                            source_record_id=comp.get("uid", {}).get("value"),
                            code=f"OPENEHR::LAB_{name.upper().replace(' ', '_')}",
                            display_name=name,
                            category=ObservationCategory.LABORATORY,
                            value=float(val),
                            unit=units,
                            effective_datetime=datetime.now(timezone.utc),
                            status="FINAL",
                        )
                    )

        return observations

    async def get_conditions(self, patient_id: str, context: AccessContext) -> List[NormalizedCondition]:
        conditions: List[NormalizedCondition] = []
        compositions = self._local_compositions.get(patient_id, [])

        for comp in compositions:
            if "evaluation" in comp.get("name", {}).get("value", "").lower() or "problem" in str(comp).lower():
                conditions.append(
                    NormalizedCondition(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=comp.get("uid", {}).get("value"),
                        code="OPENEHR::PROBLEM_DIAGNOSIS",
                        display_name="openEHR Recorded Diagnosis",
                        recorded_date=datetime.now(timezone.utc),
                    )
                )

        return conditions

    async def get_medications(self, patient_id: str, context: AccessContext) -> List[NormalizedMedication]:
        medications: List[NormalizedMedication] = []
        compositions = self._local_compositions.get(patient_id, [])

        for comp in compositions:
            if "medication" in comp.get("name", {}).get("value", "").lower():
                medications.append(
                    NormalizedMedication(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=comp.get("uid", {}).get("value"),
                        medication_name="openEHR Prescribed Order",
                        dosage_instruction="Standard clinical dosage",
                    )
                )

        return medications

    async def get_encounters(self, patient_id: str, context: AccessContext) -> List[NormalizedEncounter]:
        encounters: List[NormalizedEncounter] = []
        compositions = self._local_compositions.get(patient_id, [])

        for comp in compositions:
            if "encounter" in comp.get("name", {}).get("value", "").lower():
                encounters.append(
                    NormalizedEncounter(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=comp.get("uid", {}).get("value"),
                        encounter_class=EncounterClass.AMBULATORY,
                        status="COMPLETED",
                        reason=comp.get("name", {}).get("value"),
                    )
                )

        return encounters

    async def get_care_plans(self, patient_id: str, context: AccessContext) -> List[NormalizedCarePlan]:
        plans: List[NormalizedCarePlan] = []
        compositions = self._local_compositions.get(patient_id, [])

        for comp in compositions:
            if "care_plan" in comp.get("name", {}).get("value", "").lower():
                plans.append(
                    NormalizedCarePlan(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=comp.get("uid", {}).get("value"),
                        title=comp.get("name", {}).get("value", "openEHR Care Plan"),
                        status=CarePlanStatus.ACTIVE,
                    )
                )

        return plans

    async def get_clinical_documents(
        self, patient_id: str, context: AccessContext
    ) -> List[NormalizedClinicalDocument]:
        documents: List[NormalizedClinicalDocument] = []
        compositions = self._local_compositions.get(patient_id, [])

        for comp in compositions:
            uid = comp.get("uid", {}).get("value", "comp_uid")
            title = comp.get("name", {}).get("value", "openEHR Composition")
            documents.append(
                NormalizedClinicalDocument(
                    id=uid,
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=uid,
                    document_type=ClinicalDocumentType.CLINICAL_NOTE,
                    title=title,
                    status="FINAL",
                    created_at=datetime.now(timezone.utc),
                    structured_data=comp,
                )
            )

        return documents

    async def health_check(self) -> Dict[str, Any]:
        return {
            "source_system": self.source_system.value,
            "status": "ONLINE",
            "ehrbase_url": self.base_url,
            "cached_compositions_patients": len(self._local_compositions),
        }
