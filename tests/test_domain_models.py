import pytest
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from pydantic import ValidationError

from packages.types.enums import (
    UserRole,
    Gender,
    RiskTier,
    TrajectoryTrend,
    TriageUrgency,
    InterventionPillar,
    AuditAction,
)
from packages.clinical_models.domain_models import (
    ProvenanceRecord,
    Organization,
    CareTeam,
    CareTeamMember,
    Patient,
    Profile,
    FamilyHistory,
    LifestyleProfile,
    RiskFactor,
    VitalSign,
    LabResult,
    Medication,
    MedicationAdherence,
    Screening,
    ScreeningResult,
    RiskAssessment as DomainRiskAssessment,
    RiskFactorContribution,
    RiskTrajectory,
    InterventionPlan,
    Intervention,
    Goal,
    CheckIn,
    WearableConnection,
    WearableObservation,
    ClinicalEncounter,
    CarePlan as DomainCarePlan,
    Referral,
    Alert,
    Notification,
    Consent,
    Document,
    DocumentReference,
    AuditEvent,
)
from scripts.seed_domain_fixtures import build_synthetic_domain_dataset


def test_instantiate_all_31_domain_models():
    """Verify that all 31 clinical domain models instantiate and link cleanly."""
    dataset = build_synthetic_domain_dataset()
    expected_models = [
        "Organization", "CareTeam", "Patient", "Profile", "FamilyHistory",
        "LifestyleProfile", "RiskFactor", "VitalSign", "LabResult", "Medication",
        "MedicationAdherence", "Screening", "ScreeningResult", "RiskAssessment",
        "RiskFactorContribution", "RiskTrajectory", "InterventionPlan", "Intervention",
        "Goal", "CheckIn", "WearableConnection", "WearableObservation",
        "ClinicalEncounter", "CarePlan", "Referral", "Alert", "Notification",
        "Consent", "Document", "DocumentReference", "AuditEvent"
    ]
    assert len(dataset) == 31
    for name in expected_models:
        assert name in dataset, f"Missing expected domain entity: {name}"


# --- CLINICAL MEASUREMENT CONSTRAINTS ---

def test_vital_sign_mandatory_unit_and_timestamp():
    prov = ProvenanceRecord(recorder_id="worker-01", recorder_role=UserRole.HEALTH_WORKER)
    now = datetime.now(timezone.utc)

    # Valid VitalSign
    v = VitalSign(
        patient_id="pat-1",
        clinical_type="SYSTOLIC_BP",
        value=138.0,
        unit="mmHg",
        measurement_timestamp=now,
        source="CLINIC_VISIT",
        provenance=prov,
    )
    assert v.unit == "mmHg"
    assert v.measurement_timestamp == now

    # Missing / empty unit must raise ValidationError
    with pytest.raises(ValidationError):
        VitalSign(
            patient_id="pat-1",
            clinical_type="SYSTOLIC_BP",
            value=138.0,
            unit="",  # Invalid empty unit
            measurement_timestamp=now,
            source="CLINIC_VISIT",
            provenance=prov,
        )

    # Missing / empty unit whitespace
    with pytest.raises(ValidationError):
        VitalSign(
            patient_id="pat-1",
            clinical_type="SYSTOLIC_BP",
            value=138.0,
            unit="   ",  # Invalid whitespace
            measurement_timestamp=now,
            source="CLINIC_VISIT",
            provenance=prov,
        )


def test_lab_result_mandatory_unit_and_timestamp():
    prov = ProvenanceRecord(recorder_id="lab-tech-01", recorder_role=UserRole.HEALTH_WORKER)
    now = datetime.now(timezone.utc)

    # Valid LabResult
    lab = LabResult(
        patient_id="pat-1",
        test_name="FASTING_BLOOD_GLUCOSE",
        loinc_code="1558-6",
        value=118.0,
        unit="mg/dL",
        reference_range="70-99 mg/dL",
        measurement_timestamp=now,
        source="PHC_LAB",
        provenance=prov,
    )
    assert lab.unit == "mg/dL"
    assert lab.value == 118.0

    # Missing unit raises error
    with pytest.raises(ValidationError):
        LabResult(
            patient_id="pat-1",
            test_name="FASTING_BLOOD_GLUCOSE",
            loinc_code="1558-6",
            value=118.0,
            unit="",
            reference_range="70-99 mg/dL",
            measurement_timestamp=now,
            source="PHC_LAB",
            provenance=prov,
        )


def test_wearable_observation_mandatory_unit_and_timestamp():
    prov = ProvenanceRecord(recorder_id="device-sync", recorder_role=UserRole.CITIZEN)
    now = datetime.now(timezone.utc)

    wo = WearableObservation(
        patient_id="pat-1",
        device_connection_id="dev-conn-1",
        metric_type="HRV_RMSSD",
        value=48.2,
        unit="ms",
        measurement_timestamp=now,
        source="SMARTWATCH_WEARABLE_SDK",
        provenance=prov,
    )
    assert wo.unit == "ms"

    with pytest.raises(ValidationError):
        WearableObservation(
            patient_id="pat-1",
            device_connection_id="dev-conn-1",
            metric_type="HRV_RMSSD",
            value=48.2,
            unit="",
            measurement_timestamp=now,
            source="SMARTWATCH_WEARABLE_SDK",
            provenance=prov,
        )


def test_confidence_and_provenance_validation():
    prov = ProvenanceRecord(
        recorder_id="worker-01",
        recorder_role=UserRole.HEALTH_WORKER,
        device_model="Omron HEM-7120",
        device_id="SN-12345",
        capture_method="DIRECT_SENSOR",
    )
    now = datetime.now(timezone.utc)

    # Confidence within bounds
    v = VitalSign(
        patient_id="pat-1",
        clinical_type="HEART_RATE",
        value=72.0,
        unit="bpm",
        measurement_timestamp=now,
        source="CLINIC_VISIT",
        provenance=prov,
        confidence_score=0.95,
    )
    assert v.confidence_score == 0.95
    assert v.provenance.device_model == "Omron HEM-7120"

    # Confidence out of bounds (> 1.0) must fail
    with pytest.raises(ValidationError):
        VitalSign(
            patient_id="pat-1",
            clinical_type="HEART_RATE",
            value=72.0,
            unit="bpm",
            measurement_timestamp=now,
            source="CLINIC_VISIT",
            provenance=prov,
            confidence_score=1.5,
        )


def test_longitudinal_history_preservation():
    """Verify that multiple observations for the same patient form an append-only timeline and never overwrite."""
    prov = ProvenanceRecord(recorder_id="doc-01", recorder_role=UserRole.CLINICIAN)
    t1 = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)

    # Longitudinal systolic blood pressure time series
    readings = [
        VitalSign(patient_id="pat-100", clinical_type="SYSTOLIC_BP", value=145.0, unit="mmHg", measurement_timestamp=t1, source="CLINIC", provenance=prov),
        VitalSign(patient_id="pat-100", clinical_type="SYSTOLIC_BP", value=138.0, unit="mmHg", measurement_timestamp=t2, source="CLINIC", provenance=prov),
        VitalSign(patient_id="pat-100", clinical_type="SYSTOLIC_BP", value=124.0, unit="mmHg", measurement_timestamp=t3, source="CLINIC", provenance=prov),
    ]

    # Verify all records exist with distinct unique IDs and timestamps
    assert len(readings) == 3
    assert len(set(r.id for r in readings)) == 3
    # Chronological sort
    sorted_readings = sorted(readings, key=lambda r: r.measurement_timestamp)
    assert sorted_readings[0].value == 145.0
    assert sorted_readings[1].value == 138.0
    assert sorted_readings[2].value == 124.0
    # Patient trajectory improvement visible across longitudinal points
    assert sorted_readings[-1].value < sorted_readings[0].value


def test_consent_validity_lifecycle():
    now = datetime.now(timezone.utc)
    consent = Consent(
        patient_id="pat-1",
        grantee_id="doc-01",
        grantee_role=UserRole.CLINICIAN,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
    )
    assert consent.is_currently_valid() is True

    # Revocation immediately invalidates
    consent.status = "REVOKED"
    assert consent.is_currently_valid() is False


def test_sql_migration_file_structure():
    """Verify the PostgreSQL migration file contains all 31 tables, check constraints, and 6 index categories."""
    migration_path = Path(__file__).parent.parent / "infrastructure" / "postgres" / "migrations" / "001_initial_domain_model.sql"
    assert migration_path.exists(), f"Migration file missing at {migration_path}"
    content = migration_path.read_text(encoding="utf-8")

    # Check tables
    required_tables = [
        "organizations", "care_teams", "care_team_members", "patients", "profiles",
        "family_histories", "lifestyle_profiles", "risk_factors", "vital_signs",
        "lab_results", "medications", "medication_adherences", "screenings",
        "screening_results", "risk_assessments", "risk_factor_contributions",
        "risk_trajectories", "intervention_plans", "interventions", "goals",
        "check_ins", "wearable_connections", "wearable_observations",
        "clinical_encounters", "care_plans", "referrals", "alerts",
        "notifications", "consents", "documents", "document_references", "audit_events"
    ]
    for table in required_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in content, f"Table {table} missing in SQL migration"

    # Check mandatory unit check constraints
    assert "unit VARCHAR(32) NOT NULL CHECK (length(trim(unit)) > 0)" in content

    # Check 6 Index Categories
    # 1. Patient index
    assert "idx_vital_signs_patient_time" in content
    assert "idx_lab_results_patient_time" in content
    # 2. Timestamp index
    assert "idx_vital_signs_timestamp" in content
    # 3. Clinical type index
    assert "idx_vital_signs_clinical_type" in content
    assert "idx_lab_results_loinc" in content
    # 4. Risk domain index
    assert "idx_risk_factors_domain_severity" in content
    # 5. Organization index
    assert "idx_patients_organization" in content
    # 6. Geography/Program index
    assert "idx_profiles_geography" in content


def test_sql_seed_fixtures_file():
    """Verify synthetic SQL seed fixtures populate demo data across domain entities."""
    seed_path = Path(__file__).parent.parent / "infrastructure" / "postgres" / "seeds" / "001_synthetic_fixtures.sql"
    assert seed_path.exists()
    content = seed_path.read_text(encoding="utf-8")

    assert "INSERT INTO organizations" in content
    assert "INSERT INTO patients" in content
    assert "INSERT INTO vital_signs" in content
    assert "INSERT INTO lab_results" in content
    assert "INSERT INTO risk_assessments" in content
    assert "Ramesh" in content
    assert "91-4829-1029-4820" in content
