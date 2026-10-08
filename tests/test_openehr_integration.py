import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json

from packages.types.enums import UserRole
from packages.clinical_models.domain_models import (
    VitalSign,
    LabResult,
    ClinicalEncounter,
    CarePlan,
    ProvenanceRecord,
)
from packages.clinical_models.repository import (
    ClinicalRepository,
    PostgreSQLRepository,
    OpenEHRRepository,
    HybridClinicalRepository,
    get_clinical_repository,
)
from packages.clinical_models.openehr_builder import (
    build_ehr_status,
    build_vital_signs_composition,
    build_laboratory_composition,
    build_clinical_encounter_composition,
    build_care_plan_composition,
)


@pytest.fixture
def sample_provenance():
    return ProvenanceRecord(
        recorder_id="worker-sunita-01",
        recorder_role=UserRole.HEALTH_WORKER,
        device_model="Omron HEM-7120",
        device_id="SN-OMR-98212",
        capture_method="DIRECT_SENSOR",
    )


@pytest.mark.asyncio
async def test_patient_ehr_mapping(sample_provenance):
    """Test patient to openEHR EHR mapping with ABDM scheme."""
    repo = OpenEHRRepository()
    patient_id = "patient-ramesh-patel-01"
    abha_id = "91-4829-1029-4820"

    # Step 1: Provision openEHR EHR
    ehr_id = await repo.get_or_create_ehr(patient_id, abha_id=abha_id)
    assert ehr_id is not None
    assert len(ehr_id) > 10

    # Step 2: Idempotent lookup
    second_ehr_id = await repo.get_or_create_ehr(patient_id, abha_id=abha_id)
    assert ehr_id == second_ehr_id


@pytest.mark.asyncio
async def test_vitals_composition_and_archetypes(sample_provenance):
    """Test converting vital signs into openEHR Blood Pressure and Pulse archetypes."""
    now = datetime.now(timezone.utc)
    vitals = [
        VitalSign(
            patient_id="patient-ramesh-patel-01",
            clinical_type="SYSTOLIC_BP",
            value=138.0,
            unit="mmHg",
            measurement_timestamp=now,
            source="COMMUNITY_HEALTH_CAMP",
            provenance=sample_provenance,
            confidence_score=0.98,
        ),
        VitalSign(
            patient_id="patient-ramesh-patel-01",
            clinical_type="DIASTOLIC_BP",
            value=88.0,
            unit="mmHg",
            measurement_timestamp=now,
            source="COMMUNITY_HEALTH_CAMP",
            provenance=sample_provenance,
            confidence_score=0.98,
        ),
        VitalSign(
            patient_id="patient-ramesh-patel-01",
            clinical_type="HEART_RATE",
            value=76.0,
            unit="bpm",
            measurement_timestamp=now,
            source="COMMUNITY_HEALTH_CAMP",
            provenance=sample_provenance,
            confidence_score=0.98,
        ),
    ]

    # Verify Composition Builder
    comp = build_vital_signs_composition(vitals, composer_name="Sunita Devi")
    assert comp["_type"] == "COMPOSITION"
    assert comp["archetype_node_id"] == "openEHR-EHR-COMPOSITION.encounter.v1"
    assert len(comp["content"]) >= 2

    # Check Blood Pressure archetype
    bp_obs = next(c for c in comp["content"] if c["archetype_node_id"] == "openEHR-EHR-OBSERVATION.blood_pressure.v2")
    items = bp_obs["data"]["events"][0]["data"]["items"]
    systolic_item = next(i for i in items if i["name"]["value"] == "Systolic")
    assert systolic_item["value"]["magnitude"] == 138.0
    assert systolic_item["value"]["units"] == "mmHg"

    # Save to Repository
    repo = OpenEHRRepository()
    for v in vitals:
        uid = await repo.save_vital_sign(v)
        assert uid is not None
        assert "::" in uid or len(uid) > 10

    # Retrieve longitudinal history
    history = await repo.get_patient_vital_history("patient-ramesh-patel-01", clinical_type="SYSTOLIC_BP")
    assert len(history) >= 1
    assert history[0].value == 138.0


@pytest.mark.asyncio
async def test_laboratory_composition_and_loinc(sample_provenance):
    """Test laboratory test observation and LOINC coding in openEHR."""
    now = datetime.now(timezone.utc)
    lab = LabResult(
        patient_id="patient-ramesh-patel-01",
        test_name="FASTING_BLOOD_GLUCOSE",
        loinc_code="1558-6",
        value=118.0,
        unit="mg/dL",
        reference_range="70 - 99 mg/dL",
        interpretation="ELEVATED",
        measurement_timestamp=now,
        source="PHC_DIAGNOSTIC_LAB",
        provenance=sample_provenance,
        confidence_score=0.99,
    )

    comp = build_laboratory_composition([lab], composer_name="Dr. Radhika Rao")
    assert comp["_type"] == "COMPOSITION"
    lab_obs = comp["content"][0]
    assert lab_obs["archetype_node_id"] == "openEHR-EHR-OBSERVATION.laboratory_test_result.v1"

    repo = OpenEHRRepository()
    uid = await repo.save_lab_result(lab)
    assert uid is not None

    labs = await repo.get_patient_lab_history("patient-ramesh-patel-01", test_name="FASTING_BLOOD_GLUCOSE")
    assert len(labs) == 1
    assert labs[0].value == 118.0


@pytest.mark.asyncio
async def test_clinical_encounter_soap_composition():
    """Test storing clinical consultation encounters with SOAP notes in openEHR."""
    now = datetime.now(timezone.utc)
    encounter = ClinicalEncounter(
        patient_id="patient-ramesh-patel-01",
        clinician_id="Dr. Anand Kulkarni, MD",
        encounter_type="PHC_OPD_CONSULTATION",
        reason_for_visit="Evaluation of prediabetes and borderline vascular strain",
        soap_subjective="Patient reports fatigue after heavy carbohydrate meals.",
        soap_objective="BP 138/88 mmHg, FBG 118 mg/dL, HbA1c 6.2%",
        soap_assessment="Impaired Fasting Glycemia and Prehypertension.",
        soap_plan="Dietary millet substitution and 30-day care plan adherence tracking.",
        status="COMPLETED",
        started_at=now,
        ended_at=now + timedelta(minutes=20),
    )

    comp = build_clinical_encounter_composition(encounter)
    assert comp["_type"] == "COMPOSITION"
    soap_section = comp["content"][0]
    assert soap_section["archetype_node_id"] == "openEHR-EHR-SECTION.soap.v1"

    repo = OpenEHRRepository()
    uid = await repo.save_encounter(encounter)
    assert uid is not None

    encounters = await repo.get_patient_encounters("patient-ramesh-patel-01")
    assert len(encounters) == 1
    assert "fatigue" in encounters[0].soap_subjective


@pytest.mark.asyncio
async def test_care_plan_composition():
    """Test storing persistent openEHR care plans."""
    care_plan = CarePlan(
        patient_id="patient-ramesh-patel-01",
        lead_clinician_id="Dr. Anand Kulkarni",
        title="SevaHealth 30-Day Glycemic Stabilization Journey",
        status="ACTIVE",
    )

    comp = build_care_plan_composition(care_plan)
    assert comp["category"]["defining_code"]["code_string"] == "431"  # persistent
    assert comp["archetype_node_id"] == "openEHR-EHR-COMPOSITION.care_plan.v1"

    repo = OpenEHRRepository()
    uid = await repo.save_care_plan(care_plan)
    assert uid is not None

    plans = await repo.get_patient_care_plans("patient-ramesh-patel-01")
    assert len(plans) == 1
    assert plans[0].status == "ACTIVE"


@pytest.mark.asyncio
async def test_aql_query_execution():
    """Test Archetype Query Language (AQL) querying."""
    repo = OpenEHRRepository()
    aql = (
        "SELECT c/uid/value, o/data[at0001]/events[at0002]/data[at0003]/items[at0004]/value/magnitude "
        "FROM EHR e CONTAINS COMPOSITION c CONTAINS OBSERVATION o[openEHR-EHR-OBSERVATION.blood_pressure.v2]"
    )
    res = await repo.query_aql(aql)
    assert res is not None
    assert "q" in res
    assert "rows" in res


@pytest.mark.asyncio
async def test_hybrid_repository_synchronization(sample_provenance):
    """Test HybridClinicalRepository writes to both relational and openEHR backends."""
    now = datetime.now(timezone.utc)
    hybrid_repo = HybridClinicalRepository()

    vital = VitalSign(
        patient_id="patient-lakshmi-devi-02",
        clinical_type="SYSTOLIC_BP",
        value=164.0,
        unit="mmHg",
        measurement_timestamp=now,
        source="COMMUNITY_HEALTH_CAMP",
        provenance=sample_provenance,
        confidence_score=0.99,
        is_flagged_abnormal=True,
    )

    # Save through hybrid adapter
    comp_uid = await hybrid_repo.save_vital_sign(vital)
    assert comp_uid is not None

    # Verify both pg relational store and ehr openEHR store received record
    pg_history = await hybrid_repo.pg.get_patient_vital_history("patient-lakshmi-devi-02")
    ehr_history = await hybrid_repo.ehr.get_patient_vital_history("patient-lakshmi-devi-02")

    assert len(pg_history) == 1
    assert len(ehr_history) == 1
    assert pg_history[0].value == 164.0
    assert ehr_history[0].value == 164.0


def test_synthetic_openehr_fixtures_exist():
    """Verify generated canonical openEHR synthetic demo JSON compositions."""
    fixtures_dir = Path(__file__).parent.parent / "infrastructure" / "openehr" / "synthetic_fixtures"
    assert fixtures_dir.exists()

    required_fixtures = [
        "ramesh_patel_vitals_composition.json",
        "ramesh_patel_labs_composition.json",
        "ramesh_patel_encounter_composition.json",
        "ramesh_patel_care_plan_composition.json",
        "lakshmi_devi_hypertension_composition.json",
        "priya_sharma_baseline_composition.json",
    ]
    for filename in required_fixtures:
        filepath = fixtures_dir / filename
        assert filepath.exists(), f"Missing synthetic openEHR fixture: {filename}"
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert data["_type"] == "COMPOSITION"
        assert "archetype_node_id" in data
        assert "content" in data
