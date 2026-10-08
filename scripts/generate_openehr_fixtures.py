import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import uuid

# Ensure sevahealth-ai is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.types.enums import UserRole

from packages.clinical_models.domain_models import (
    VitalSign,
    LabResult,
    ClinicalEncounter,
    CarePlan,
    ProvenanceRecord,
)
from packages.clinical_models.openehr_builder import (
    build_ehr_status,
    build_vital_signs_composition,
    build_laboratory_composition,
    build_clinical_encounter_composition,
    build_care_plan_composition,
)


def generate_all_openehr_demo_fixtures():
    output_dir = Path(__file__).parent.parent / "infrastructure" / "openehr" / "synthetic_fixtures"
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    # 1. Ramesh Patel: Vitals Composition (Prediabetes & Pre-HTN)
    ramesh_prov = ProvenanceRecord(
        recorder_id="worker-sunita-01",
        recorder_role=UserRole.HEALTH_WORKER,
        device_model="Omron HEM-7120",
        device_id="SN-OMR-98212",
        capture_method="DIRECT_SENSOR",
    )
    ramesh_vitals = [
        VitalSign(
            patient_id="citizen-ramesh-patel-01",
            clinical_type="SYSTOLIC_BP",
            value=138.0,
            unit="mmHg",
            measurement_timestamp=now - timedelta(days=7),
            source="COMMUNITY_HEALTH_CAMP",
            provenance=ramesh_prov,
            confidence_score=0.98,
        ),
        VitalSign(
            patient_id="citizen-ramesh-patel-01",
            clinical_type="DIASTOLIC_BP",
            value=88.0,
            unit="mmHg",
            measurement_timestamp=now - timedelta(days=7),
            source="COMMUNITY_HEALTH_CAMP",
            provenance=ramesh_prov,
            confidence_score=0.98,
        ),
        VitalSign(
            patient_id="citizen-ramesh-patel-01",
            clinical_type="HEART_RATE",
            value=76.0,
            unit="bpm",
            measurement_timestamp=now - timedelta(days=7),
            source="COMMUNITY_HEALTH_CAMP",
            provenance=ramesh_prov,
            confidence_score=0.98,
        ),
        VitalSign(
            patient_id="citizen-ramesh-patel-01",
            clinical_type="BMI",
            value=27.2,
            unit="kg/m2",
            measurement_timestamp=now - timedelta(days=7),
            source="COMMUNITY_HEALTH_CAMP",
            provenance=ramesh_prov,
            confidence_score=1.0,
        ),
        VitalSign(
            patient_id="citizen-ramesh-patel-01",
            clinical_type="WAIST_CIRCUMFERENCE",
            value=96.0,
            unit="cm",
            measurement_timestamp=now - timedelta(days=7),
            source="COMMUNITY_HEALTH_CAMP",
            provenance=ramesh_prov,
            confidence_score=1.0,
        ),
    ]
    vitals_comp = build_vital_signs_composition(
        vitals=ramesh_vitals,
        composer_name="Sunita Devi (ASHA Worker)",
        facility_name="Ward 12 Community Health Camp, Devanahalli",
    )
    (output_dir / "ramesh_patel_vitals_composition.json").write_text(json.dumps(vitals_comp, indent=2), encoding="utf-8")

    # 2. Ramesh Patel: Labs Composition
    ramesh_lab_prov = ProvenanceRecord(
        recorder_id="nanjangud-phc-lab",
        recorder_role=UserRole.HEALTH_WORKER,
        device_model="Roche Cobas b 101",
    )
    ramesh_labs = [
        LabResult(
            patient_id="citizen-ramesh-patel-01",
            test_name="FASTING_BLOOD_GLUCOSE",
            loinc_code="1558-6",
            value=118.0,
            unit="mg/dL",
            reference_range="70 - 99 mg/dL",
            interpretation="ELEVATED",
            measurement_timestamp=now - timedelta(days=7),
            source="PHC_DIAGNOSTIC_LAB",
            provenance=ramesh_lab_prov,
        ),
        LabResult(
            patient_id="citizen-ramesh-patel-01",
            test_name="HBA1C",
            loinc_code="4548-4",
            value=6.2,
            unit="%",
            reference_range="< 5.7 %",
            interpretation="ELEVATED",
            measurement_timestamp=now - timedelta(days=7),
            source="PHC_DIAGNOSTIC_LAB",
            provenance=ramesh_lab_prov,
        ),
        LabResult(
            patient_id="citizen-ramesh-patel-01",
            test_name="TRIGLYCERIDES",
            loinc_code="2571-8",
            value=185.0,
            unit="mg/dL",
            reference_range="< 150 mg/dL",
            interpretation="ELEVATED",
            measurement_timestamp=now - timedelta(days=7),
            source="PHC_DIAGNOSTIC_LAB",
            provenance=ramesh_lab_prov,
        ),
    ]
    labs_comp = build_laboratory_composition(
        labs=ramesh_labs,
        composer_name="Dr. Radhika Rao (Pathologist)",
        facility_name="Nanjangud Primary Health Centre",
    )
    (output_dir / "ramesh_patel_labs_composition.json").write_text(json.dumps(labs_comp, indent=2), encoding="utf-8")

    # 3. Ramesh Patel: Encounter SOAP Composition
    ramesh_encounter = ClinicalEncounter(
        patient_id="citizen-ramesh-patel-01",
        clinician_id="Dr. Anand Kulkarni, MD",
        encounter_type="PHC_OPD_CONSULTATION",
        reason_for_visit="Evaluation of prediabetes and borderline vascular strain",
        soap_subjective="48yo male screened with high IDRS (60/100). Reports occasional postprandial fatigue. Denies chest pain or exertional dyspnea.",
        soap_objective="BP 138/88 mmHg. Fasting blood sugar 118 mg/dL, HbA1c 6.2%, Waist 96 cm, BMI 27.2 kg/m2.",
        soap_assessment="Impaired Fasting Glycemia (Prediabetes) and Prehypertension with Asian Indian central adiposity.",
        soap_plan="1. Structured 30-day glycemic stabilization care plan. 2. Foxtail millet substitution. 3. 20-minute post-dinner brisk walk. 4. Re-check FBG in 30 days.",
        status="COMPLETED",
        started_at=now - timedelta(days=7),
        ended_at=now - timedelta(days=7) + timedelta(minutes=20),
    )
    encounter_comp = build_clinical_encounter_composition(ramesh_encounter)
    (output_dir / "ramesh_patel_encounter_composition.json").write_text(json.dumps(encounter_comp, indent=2), encoding="utf-8")

    # 4. Ramesh Patel: Care Plan Composition
    ramesh_care_plan = CarePlan(
        patient_id="citizen-ramesh-patel-01",
        lead_clinician_id="Dr. Anand Kulkarni, MD",
        title="SevaHealth 30-Day Glycemic Stabilization Journey",
        status="ACTIVE",
    )
    care_plan_comp = build_care_plan_composition(ramesh_care_plan)
    (output_dir / "ramesh_patel_care_plan_composition.json").write_text(json.dumps(care_plan_comp, indent=2), encoding="utf-8")

    # 5. Lakshmi Devi: Stage 2 Severe Hypertension Composition
    lakshmi_prov = ProvenanceRecord(
        recorder_id="worker-sunita-01",
        recorder_role=UserRole.HEALTH_WORKER,
        device_model="Omron HEM-7120",
    )
    lakshmi_vitals = [
        VitalSign(
            patient_id="citizen-lakshmi-devi-02",
            clinical_type="SYSTOLIC_BP",
            value=164.0,
            unit="mmHg",
            measurement_timestamp=now - timedelta(days=2),
            source="COMMUNITY_HEALTH_CAMP",
            provenance=lakshmi_prov,
            confidence_score=0.99,
            is_flagged_abnormal=True,
        ),
        VitalSign(
            patient_id="citizen-lakshmi-devi-02",
            clinical_type="DIASTOLIC_BP",
            value=98.0,
            unit="mmHg",
            measurement_timestamp=now - timedelta(days=2),
            source="COMMUNITY_HEALTH_CAMP",
            provenance=lakshmi_prov,
            confidence_score=0.99,
            is_flagged_abnormal=True,
        ),
    ]
    lakshmi_comp = build_vital_signs_composition(
        vitals=lakshmi_vitals,
        composer_name="Sunita Devi (ASHA)",
        facility_name="Koppa Health Camp, Mandya",
    )
    (output_dir / "lakshmi_devi_hypertension_composition.json").write_text(json.dumps(lakshmi_comp, indent=2), encoding="utf-8")

    # 6. Priya Sharma: Healthy Baseline Composition
    priya_prov = ProvenanceRecord(
        recorder_id="mysuru-wellness-clinic",
        recorder_role=UserRole.CLINICIAN,
        device_model="Welch Allyn 767",
    )
    priya_vitals = [
        VitalSign(
            patient_id="citizen-priya-sharma-04",
            clinical_type="SYSTOLIC_BP",
            value=116.0,
            unit="mmHg",
            measurement_timestamp=now - timedelta(days=14),
            source="CLINIC_VISIT",
            provenance=priya_prov,
            confidence_score=1.0,
        ),
        VitalSign(
            patient_id="citizen-priya-sharma-04",
            clinical_type="DIASTOLIC_BP",
            value=76.0,
            unit="mmHg",
            measurement_timestamp=now - timedelta(days=14),
            source="CLINIC_VISIT",
            provenance=priya_prov,
            confidence_score=1.0,
        ),
        VitalSign(
            patient_id="citizen-priya-sharma-04",
            clinical_type="HEART_RATE",
            value=68.0,
            unit="bpm",
            measurement_timestamp=now - timedelta(days=14),
            source="CLINIC_VISIT",
            provenance=priya_prov,
            confidence_score=1.0,
        ),
    ]
    priya_comp = build_vital_signs_composition(
        vitals=priya_vitals,
        composer_name="Dr. Anand Kulkarni",
        facility_name="Mysuru Wellness & Preventive Clinic",
    )
    (output_dir / "priya_sharma_baseline_composition.json").write_text(json.dumps(priya_comp, indent=2), encoding="utf-8")

    print(f"[OK] Generated 6 canonical openEHR synthetic composition fixtures in {output_dir}")


if __name__ == "__main__":
    generate_all_openehr_demo_fixtures()
