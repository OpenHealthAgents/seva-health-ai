"""SevaHealth Local Clinical Data Adapter.

Extracts data from the local transactional store (citizens, observations,
screenings, care plans, medications, legal clinical records) and maps to
normalized internal clinical models.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import structlog

from packages.types.enums import UserRole
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
    ConditionClinicalStatus,
    ConditionVerificationStatus,
    MedicationStatus,
    CarePlanStatus,
    ClinicalDocumentType,
    EncounterClass,
)
from services.store import store

logger = structlog.get_logger(__name__)


class SevaHealthLocalAdapter(ClinicalDataProvider):
    """Adapter bridging SevaHealth's primary transactional store to normalized clinical models."""

    @property
    def source_system(self) -> ClinicalSourceSystem:
        return ClinicalSourceSystem.SEVAHEALTH_LOCAL

    async def get_patient(self, patient_id: str, context: AccessContext) -> Optional[NormalizedPatient]:
        citizen = store.get_citizen(patient_id)
        if not citizen:
            return None

        return NormalizedPatient(
            id=citizen.id,
            national_id=citizen.abha_id,
            source_system=self.source_system,
            source_patient_id=citizen.id,
            name=f"{citizen.first_name} {citizen.last_name}",
            first_name=citizen.first_name,
            last_name=citizen.last_name,
            gender=citizen.gender.value if hasattr(citizen.gender, "value") else str(citizen.gender),
            birth_date=citizen.birth_date,
            phone=citizen.phone,
            address={
                "state": citizen.state,
                "district": citizen.district,
                "sub_district": citizen.sub_district,
                "village_or_ward": citizen.village_or_ward,
            },
            active=True,
            metadata={
                "tenant_id": citizen.tenant_id,
                "user_id": citizen.user_id,
                "primary_language": citizen.primary_language,
            },
        )

    async def get_observations(
        self,
        patient_id: str,
        context: AccessContext,
        category: Optional[ObservationCategory] = None,
    ) -> List[NormalizedObservation]:
        local_obs_list = store.get_citizen_observations(patient_id)
        normalized = []

        for obs in local_obs_list:
            # Map category
            cat = ObservationCategory.VITAL_SIGN
            obs_type = getattr(obs, "observation_type", "").upper()
            if any(lab_kw in obs_type for lab_kw in ["HBA1C", "GLUCOSE", "CHOLESTEROL", "CREATININE", "EGFR", "LAB"]):
                cat = ObservationCategory.LABORATORY
            elif "LIFESTYLE" in obs_type or "ACTIVITY" in obs_type:
                cat = ObservationCategory.LIFESTYLE

            if category and cat != category:
                continue

            dt = getattr(obs, "effective_datetime", None) or getattr(obs, "recorded_at", None)
            if not isinstance(dt, datetime):
                dt = datetime.now(timezone.utc)

            normalized.append(
                NormalizedObservation(
                    id=getattr(obs, "id", None) or str(obs.code),
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=getattr(obs, "id", None),
                    code=getattr(obs, "code", "UNKNOWN"),
                    display_name=getattr(obs, "display_name", getattr(obs, "code", "Observation")),
                    category=cat,
                    value=float(getattr(obs, "value", 0.0)),
                    unit=getattr(obs, "unit", ""),
                    interpretation=getattr(obs, "interpretation", None),
                    effective_datetime=dt,
                    status="FINAL",
                    metadata={
                        "device_id": getattr(obs, "device_id", None),
                        "performer": getattr(obs, "performer", None),
                    },
                )
            )

        return normalized

    async def get_conditions(self, patient_id: str, context: AccessContext) -> List[NormalizedCondition]:
        conditions: List[NormalizedCondition] = []
        # Check screenings or risk factors
        screenings = store.get_citizen_screenings(patient_id)
        for s in screenings:
            risks = getattr(s, "risk_factors", [])
            for r in risks:
                conditions.append(
                    NormalizedCondition(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=str(getattr(s, "id", "local_screening")),
                        code=getattr(r, "code", "NCD-RISK"),
                        display_name=getattr(r, "name", str(r)),
                        clinical_status=ConditionClinicalStatus.ACTIVE,
                        verification_status=ConditionVerificationStatus.PROVISIONAL,
                        severity="MODERATE",
                        recorded_date=getattr(s, "timestamp", datetime.now(timezone.utc)),
                    )
                )

        # Check confirmed legal clinical records
        legal_records = store.get_legal_clinical_records(patient_id)
        for rec in legal_records:
            if rec.get("record_type") == "CONDITION" or "diagnosis" in rec:
                conditions.append(
                    NormalizedCondition(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=rec.get("record_id"),
                        code=rec.get("code", "R69"),
                        display_name=rec.get("display_name", rec.get("diagnosis", "Clinical Diagnosis")),
                        clinical_status=ConditionClinicalStatus.ACTIVE,
                        verification_status=ConditionVerificationStatus.CONFIRMED,
                        severity=rec.get("severity", "MODERATE"),
                        recorded_date=datetime.now(timezone.utc),
                        notes=rec.get("notes"),
                    )
                )

        return conditions

    async def get_medications(self, patient_id: str, context: AccessContext) -> List[NormalizedMedication]:
        meds_raw = store.medications.get(patient_id, [])
        normalized: List[NormalizedMedication] = []

        for m in meds_raw:
            if isinstance(m, dict):
                normalized.append(
                    NormalizedMedication(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=m.get("id"),
                        code=m.get("code"),
                        medication_name=m.get("medication_name", m.get("name", "Unknown Medication")),
                        dosage_instruction=m.get("dosage_instruction", m.get("dosage", "As directed")),
                        status=MedicationStatus.ACTIVE if m.get("status") in ["ACTIVE", "active", None] else MedicationStatus.STOPPED,
                        route=m.get("route", "ORAL"),
                        start_date=m.get("start_date"),
                        end_date=m.get("end_date"),
                        prescriber_name=m.get("prescriber"),
                        reason=m.get("indication"),
                    )
                )
            else:
                normalized.append(
                    NormalizedMedication(
                        patient_id=patient_id,
                        source_system=self.source_system,
                        medication_name=getattr(m, "medication_name", str(m)),
                        dosage_instruction=getattr(m, "dosage", "As prescribed"),
                        status=MedicationStatus.ACTIVE,
                    )
                )

        return normalized

    async def get_encounters(self, patient_id: str, context: AccessContext) -> List[NormalizedEncounter]:
        encounters_raw = store.encounters.get(patient_id, [])
        normalized: List[NormalizedEncounter] = []

        for enc in encounters_raw:
            if isinstance(enc, dict):
                normalized.append(
                    NormalizedEncounter(
                        id=enc.get("id") or str(len(normalized) + 1),
                        patient_id=patient_id,
                        source_system=self.source_system,
                        source_record_id=enc.get("id"),
                        encounter_class=EncounterClass.FIELD_VISIT if enc.get("class") == "FIELD" else EncounterClass.AMBULATORY,
                        status=enc.get("status", "COMPLETED"),
                        reason=enc.get("reason"),
                        soap_note=enc.get("soap_note"),
                        period_start=datetime.now(timezone.utc),
                        provider_name=enc.get("provider_name"),
                        facility_name=enc.get("facility_name"),
                    )
                )

        return normalized

    async def get_care_plans(self, patient_id: str, context: AccessContext) -> List[NormalizedCarePlan]:
        normalized: List[NormalizedCarePlan] = []
        # Check standard care plan
        plan = store.care_plans.get(patient_id)
        if plan:
            normalized.append(
                NormalizedCarePlan(
                    id=getattr(plan, "id", "local_care_plan"),
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=getattr(plan, "id", None),
                    title=getattr(plan, "title", "Personalized Prevention Plan"),
                    status=CarePlanStatus.ACTIVE,
                    intent="PREVENTION",
                    goals=[{"title": g} for g in getattr(plan, "goals", [])],
                    activities=[{"name": getattr(t, "title", str(t))} for t in getattr(plan, "daily_tasks", [])],
                )
            )

        # Check comprehensive care plan
        comp_plan = store.comprehensive_care_plans.get(patient_id)
        if comp_plan:
            normalized.append(
                NormalizedCarePlan(
                    id=getattr(comp_plan, "id", "comp_care_plan"),
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=getattr(comp_plan, "id", None),
                    title=getattr(comp_plan, "title", "30-Day NCD Prevention Plan"),
                    status=CarePlanStatus.ACTIVE,
                    intent="PREVENTION",
                    goals=[g.dict() if hasattr(g, "dict") else str(g) for g in getattr(comp_plan, "goals", [])],
                    activities=[a.dict() if hasattr(a, "dict") else str(a) for a in getattr(comp_plan, "interventions", [])],
                )
            )

        return normalized

    async def get_clinical_documents(
        self, patient_id: str, context: AccessContext
    ) -> List[NormalizedClinicalDocument]:
        docs_raw = store.documents.get(patient_id, [])
        normalized: List[NormalizedClinicalDocument] = []

        for d in docs_raw:
            doc_type = ClinicalDocumentType.CLINICAL_NOTE
            dtype_str = d.get("document_type", "").upper()
            if "LAB" in dtype_str:
                doc_type = ClinicalDocumentType.LAB_REPORT
            elif "DISCHARGE" in dtype_str:
                doc_type = ClinicalDocumentType.DISCHARGE_SUMMARY
            elif "PRESCRIPTION" in dtype_str:
                doc_type = ClinicalDocumentType.PRESCRIPTION

            normalized.append(
                NormalizedClinicalDocument(
                    id=d.get("id") or str(len(normalized) + 1),
                    patient_id=patient_id,
                    source_system=self.source_system,
                    source_record_id=d.get("id"),
                    document_type=doc_type,
                    title=d.get("title", "Clinical Document"),
                    status="FINAL",
                    created_at=datetime.now(timezone.utc),
                    author=d.get("author"),
                    content_text=d.get("content_text") or d.get("summary"),
                    structured_data=d.get("structured_data"),
                )
            )

        return normalized

    async def health_check(self) -> Dict[str, Any]:
        return {
            "source_system": self.source_system.value,
            "status": "ONLINE",
            "citizens_count": len(store.citizens),
            "observations_count": sum(len(v) for v in store.observations.values()),
        }
