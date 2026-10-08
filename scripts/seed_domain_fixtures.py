import sys
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
import uuid

# Ensure sevahealth-ai is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    RiskAssessment,
    RiskFactorContribution,
    RiskTrajectory,
    InterventionPlan,
    Intervention,
    Goal,
    CheckIn,
    WearableConnection,
    WearableObservation,
    ClinicalEncounter,
    CarePlan,
    Referral,
    Alert,
    Notification,
    Consent,
    Document,
    DocumentReference,
    AuditEvent,
)


def build_synthetic_domain_dataset():
    """Builds a cohesive synthetic dataset across all 31 SevaHealth domain entities."""
    now = datetime.now(timezone.utc)
    one_month_ago = now - timedelta(days=30)
    one_week_ago = now - timedelta(days=7)

    # 1. Organization
    org = Organization(
        id=str(uuid.uuid4()),
        name="Karnataka State Health Mission - Mysuru District",
        type="DISTRICT_HEALTH_OFFICE",
        jurisdiction="Mysuru District",
    )

    # 2. CareTeam
    care_team = CareTeam(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        name="Ward 12 NCD Prevention Cell",
        jurisdiction="Ward 12, Devanahalli",
        members=[
            CareTeamMember(user_id="worker-01", role=UserRole.HEALTH_WORKER, name="Sunita Devi (ASHA)", phone="+91 98450 11111"),
            CareTeamMember(user_id="doctor-01", role=UserRole.CLINICIAN, name="Dr. Anand Kulkarni, MD", phone="+91 98450 22222"),
        ]
    )

    # 3. Patient
    patient = Patient(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        abha_id="91-4829-1029-4820",
        user_id="citizen-ramesh-user",
        primary_care_team_id=care_team.id,
    )

    # 4. Profile
    profile = Profile(
        patient_id=patient.id,
        first_name="Ramesh",
        last_name="Patel",
        birth_date=date(1978, 4, 12),
        gender=Gender.MALE,
        phone="+91 98450 12345",
        email="ramesh.patel@sevahealth.ai",
        state="Karnataka",
        district="Bengaluru Rural",
        sub_district="Devanahalli",
        village_or_ward="Ward 12",
        primary_language="kn",
        socioeconomic_tier="BPL",
    )

    # 5. FamilyHistory
    fam_history = [
        FamilyHistory(
            patient_id=patient.id,
            relative_relationship="FATHER",
            condition_code="DIABETES_MELLITUS_TYPE_2",
            condition_name="Type 2 Diabetes Mellitus",
            age_at_onset=52,
            is_deceased=True,
        ),
        FamilyHistory(
            patient_id=patient.id,
            relative_relationship="MOTHER",
            condition_code="HYPERTENSION",
            condition_name="Essential Hypertension",
            age_at_onset=58,
            is_deceased=False,
        )
    ]

    # 6. LifestyleProfile
    lifestyle = LifestyleProfile(
        patient_id=patient.id,
        tobacco_use="NEVER",
        alcohol_use="NONE",
        dietary_pattern="HIGH_CARB_HIGH_SALT",
        physical_activity_level="SEDENTARY",
        sleep_hours_per_night=6.0,
        perceived_stress_level="MODERATE",
    )

    # 7. RiskFactor
    risk_factors = [
        RiskFactor(patient_id=patient.id, domain="DIABETES", name="IMPAIRED_FASTING_GLYCEMIA", severity="HIGH"),
        RiskFactor(patient_id=patient.id, domain="HYPERTENSION", name="PREHYPERTENSION_VASCULAR_STRAIN", severity="MODERATE"),
        RiskFactor(patient_id=patient.id, domain="METABOLIC", name="CENTRAL_VISCERAL_ADIPOSITY", severity="HIGH"),
    ]

    # Standard Clinical Provenance
    asha_provenance = ProvenanceRecord(
        recorder_id="worker-01",
        recorder_role=UserRole.HEALTH_WORKER,
        device_model="Omron HEM-7120 Digital Sphygmomanometer",
        device_id="SN-OMR-98212",
        capture_method="DIRECT_SENSOR",
    )
    doctor_provenance = ProvenanceRecord(
        recorder_id="doctor-01",
        recorder_role=UserRole.CLINICIAN,
        device_model="Welch Allyn 767 Wall Aneroid",
        device_id="SN-WA-4410",
        capture_method="CLINICIAN_ENTERED",
    )

    # 8. Longitudinal Vital Signs (Demonstrates historical series: visit 1 vs visit 2)
    vitals_history = [
        # Visit 1 (30 days ago)
        VitalSign(
            patient_id=patient.id,
            clinical_type="SYSTOLIC_BP",
            value=142.0,
            unit="mmHg",
            measurement_timestamp=one_month_ago,
            source="COMMUNITY_HEALTH_CAMP",
            provenance=asha_provenance,
            confidence_score=0.95,
            is_flagged_abnormal=True,
        ),
        VitalSign(
            patient_id=patient.id,
            clinical_type="DIASTOLIC_BP",
            value=90.0,
            unit="mmHg",
            measurement_timestamp=one_month_ago,
            source="COMMUNITY_HEALTH_CAMP",
            provenance=asha_provenance,
            confidence_score=0.95,
            is_flagged_abnormal=True,
        ),
        VitalSign(
            patient_id=patient.id,
            clinical_type="WAIST_CIRCUMFERENCE",
            value=97.0,
            unit="cm",
            measurement_timestamp=one_month_ago,
            source="COMMUNITY_HEALTH_CAMP",
            provenance=asha_provenance,
            confidence_score=1.0,
        ),
        # Visit 2 (Follow-up 7 days ago - Notice improvement, previous records are strictly preserved!)
        VitalSign(
            patient_id=patient.id,
            clinical_type="SYSTOLIC_BP",
            value=138.0,
            unit="mmHg",
            measurement_timestamp=one_week_ago,
            source="PHC_OPD_CONSULTATION",
            provenance=doctor_provenance,
            confidence_score=0.98,
            is_flagged_abnormal=True,
        ),
        VitalSign(
            patient_id=patient.id,
            clinical_type="DIASTOLIC_BP",
            value=88.0,
            unit="mmHg",
            measurement_timestamp=one_week_ago,
            source="PHC_OPD_CONSULTATION",
            provenance=doctor_provenance,
            confidence_score=0.98,
        ),
    ]

    # 9. LabResult
    lab_provenance = ProvenanceRecord(
        recorder_id="phc-lab-technician-01",
        recorder_role=UserRole.HEALTH_WORKER,
        device_model="Roche Cobas b 101 POCT Analyzer",
        device_id="SN-COBAS-3319",
        capture_method="DIRECT_SENSOR",
    )
    labs = [
        LabResult(
            patient_id=patient.id,
            test_name="FASTING_BLOOD_GLUCOSE",
            loinc_code="1558-6",
            value=118.0,
            unit="mg/dL",
            reference_range="70 - 99 mg/dL",
            interpretation="ELEVATED",
            measurement_timestamp=one_week_ago,
            source="PHC_DIAGNOSTIC_LAB",
            provenance=lab_provenance,
            confidence_score=0.99,
        ),
        LabResult(
            patient_id=patient.id,
            test_name="HBA1C",
            loinc_code="4548-4",
            value=6.2,
            unit="%",
            reference_range="< 5.7 %",
            interpretation="ELEVATED",
            measurement_timestamp=one_week_ago,
            source="PHC_DIAGNOSTIC_LAB",
            provenance=lab_provenance,
            confidence_score=0.99,
        ),
    ]

    # 10. Medication
    med = Medication(
        patient_id=patient.id,
        drug_name="Metformin Hydrochloride",
        dosage="500 mg",
        frequency="Once Daily with Dinner",
        indication="Impaired Glycemia / Prediabetes Reversal",
        prescribed_by="Dr. Anand Kulkarni",
        start_date=date.today() - timedelta(days=6),
    )

    # 11. MedicationAdherence
    adherence_logs = [
        MedicationAdherence(patient_id=patient.id, medication_id=med.id, scheduled_date=date.today() - timedelta(days=2), taken=True),
        MedicationAdherence(patient_id=patient.id, medication_id=med.id, scheduled_date=date.today() - timedelta(days=1), taken=True),
        MedicationAdherence(patient_id=patient.id, medication_id=med.id, scheduled_date=date.today(), taken=True),
    ]

    # 12. Screening
    screening = Screening(
        patient_id=patient.id,
        screening_type="NCD_COMPREHENSIVE_CBAC",
        administered_by="Sunita Devi",
        administrator_role=UserRole.HEALTH_WORKER,
        location="Ward 12 Community Health Hall",
        screened_at=one_month_ago,
    )

    # 13. ScreeningResult
    screening_result = ScreeningResult(
        screening_id=screening.id,
        patient_id=patient.id,
        cbac_score=7,
        idrs_score=60,
        needs_immediate_referral=True,
        summary_findings="Elevated IDRS (60/100) and CBAC score (7) demonstrate substantial risk of progression to Type 2 Diabetes.",
    )

    # 14. RiskAssessment
    risk_assessment = RiskAssessment(
        patient_id=patient.id,
        screening_id=screening.id,
        overall_score=0.68,
        overall_tier=RiskTier.HIGH,
        domain_scores={"diabetes": 0.74, "hypertension": 0.62, "metabolic": 0.70, "cardiovascular": 0.45},
        assessed_at=one_month_ago,
    )

    # 15. RiskFactorContribution
    contributions = [
        RiskFactorContribution(
            risk_assessment_id=risk_assessment.id,
            patient_id=patient.id,
            factor_name="Prediabetic Impaired Glycemia",
            factor_category="BIOMETRIC",
            observed_value="HbA1c 6.2%, FBG 118 mg/dL",
            target_value="HbA1c < 5.7%",
            relative_weight=0.26,
            evidence_guideline="ICMR-INDIAB Guidelines 2023",
        ),
        RiskFactorContribution(
            risk_assessment_id=risk_assessment.id,
            patient_id=patient.id,
            factor_name="Prehypertension Vascular Strain",
            factor_category="BIOMETRIC",
            observed_value="138/88 mmHg",
            target_value="< 120/80 mmHg",
            relative_weight=0.19,
            evidence_guideline="ACC/AHA 2017 Guidelines",
        ),
        RiskFactorContribution(
            risk_assessment_id=risk_assessment.id,
            patient_id=patient.id,
            factor_name="Tobacco Abstinence",
            factor_category="LIFESTYLE",
            observed_value="Non-smoker",
            target_value="Non-smoker",
            relative_weight=-0.12,
            is_protective=True,
            evidence_guideline="WHO Essential Interventions",
        ),
    ]

    # 16. RiskTrajectory
    trajectory = RiskTrajectory(
        patient_id=patient.id,
        assessment_ids=[risk_assessment.id],
        historical_scores=[{"date": one_month_ago.isoformat(), "score": 0.68}],
        trend=TrajectoryTrend.DETERIORATING,
        rate_of_change=0.045,
        projected_tier_6m=RiskTier.CRITICAL,
    )

    # 17. InterventionPlan
    plan = InterventionPlan(
        patient_id=patient.id,
        risk_assessment_id=risk_assessment.id,
        title="SevaHealth 30-Day Glycemic Stabilization Journey",
        primary_domain="Prediabetes & Vascular Protection",
        start_date=date.today() - timedelta(days=7),
        end_date=date.today() + timedelta(days=23),
        adherence_rate=23.3,
    )

    # 18. Intervention
    interventions = [
        Intervention(
            plan_id=plan.id,
            pillar=InterventionPillar.NUTRITION,
            title="Swap White Rice with Foxtail Millet",
            prescription_text="Replace 50% of refined polished grains with ragi or foxtail millet.",
            frequency="Daily with lunch",
            target_metric="1 serving",
        ),
        Intervention(
            plan_id=plan.id,
            pillar=InterventionPillar.PHYSICAL_ACTIVITY,
            title="Post-Dinner 20-Min Brisk Walk",
            prescription_text="Blunts post-prandial glycemic excursions by 28%.",
            frequency="Daily after dinner",
            target_metric="2,500 steps",
        )
    ]

    # 19. Goal
    goals = [
        Goal(patient_id=patient.id, plan_id=plan.id, metric_name="FASTING_GLUCOSE", baseline_value=118.0, target_value=99.0, target_date=date.today() + timedelta(days=23)),
        Goal(patient_id=patient.id, plan_id=plan.id, metric_name="SYSTOLIC_BP", baseline_value=138.0, target_value=120.0, target_date=date.today() + timedelta(days=23)),
    ]

    # 20. CheckIn
    check_in = CheckIn(
        patient_id=patient.id,
        plan_id=plan.id,
        check_in_date=date.today(),
        tasks_completed_count=7,
        tasks_total_count=7,
        subjective_wellbeing="GOOD",
    )

    # 21. WearableConnection
    wearable_conn = WearableConnection(
        patient_id=patient.id,
        device_brand="Noise",
        device_model="ColorFit Pro 4",
        connection_status="CONNECTED",
        last_synced_at=now,
    )

    # 22. Longitudinal Wearable Observations
    wearable_prov = ProvenanceRecord(
        recorder_id="patient-app-sync",
        recorder_role=UserRole.CITIZEN,
        device_model="Noise ColorFit Pro 4",
        device_id="BLE-DEV-9812",
        capture_method="DIRECT_SENSOR",
    )
    wearable_obs = [
        WearableObservation(
            patient_id=patient.id,
            device_connection_id=wearable_conn.id,
            metric_type="RESTING_HEART_RATE",
            value=72.0,
            unit="bpm",
            measurement_timestamp=now - timedelta(hours=6),
            source="SMARTWATCH_WEARABLE_SDK",
            provenance=wearable_prov,
            confidence_score=0.94,
            rolling_7d_baseline=73.5,
        ),
        WearableObservation(
            patient_id=patient.id,
            device_connection_id=wearable_conn.id,
            metric_type="HRV_RMSSD",
            value=48.2,
            unit="ms",
            measurement_timestamp=now - timedelta(hours=6),
            source="SMARTWATCH_WEARABLE_SDK",
            provenance=wearable_prov,
            confidence_score=0.92,
            rolling_7d_baseline=45.0,
        ),
        WearableObservation(
            patient_id=patient.id,
            device_connection_id=wearable_conn.id,
            metric_type="DAILY_STEPS",
            value=7450.0,
            unit="steps",
            measurement_timestamp=now - timedelta(hours=1),
            source="SMARTWATCH_WEARABLE_SDK",
            provenance=wearable_prov,
            confidence_score=0.99,
            rolling_7d_baseline=6800.0,
        ),
    ]

    # 23. ClinicalEncounter
    encounter = ClinicalEncounter(
        patient_id=patient.id,
        clinician_id="doctor-01",
        encounter_type="PHC_OPD_CONSULTATION",
        reason_for_visit="Evaluation of prediabetes and borderline vascular strain",
        soap_subjective="Patient reports occasional post-meal fatigue. Adhering to millet substitutions.",
        soap_objective="BP 138/88 mmHg, FBG 118 mg/dL, HbA1c 6.2%, Waist 96 cm.",
        soap_assessment="Impaired Fasting Glycemia (Prediabetes) and Prehypertension.",
        soap_plan="Prescribed Metformin 500mg daily, low-glycemic dietary calibration, and 30-day care plan adherence tracking.",
        status="COMPLETED",
        started_at=one_week_ago,
        ended_at=one_week_ago + timedelta(minutes=25),
    )

    # 24. CarePlan
    care_plan = CarePlan(
        patient_id=patient.id,
        care_team_id=care_team.id,
        lead_clinician_id="doctor-01",
        title="Integrated Primary Prevention & Glycemic Care Plan",
        status="ACTIVE",
    )

    # 25. Referral
    referral = Referral(
        patient_id=patient.id,
        referring_worker_id="worker-01",
        referred_to_facility="Nanjangud PHC Medical Officer",
        urgency=TriageUrgency.PRIORITY,
        clinical_reason="High CBAC score (7) and elevated blood pressure at field screening.",
        status="COMPLETED",
        completed_at=one_week_ago,
    )

    # 26. Alert
    alert = Alert(
        patient_id=patient.id,
        urgency=TriageUrgency.PRIORITY,
        alert_type="GLYCEMIC_DETERIORATION",
        message="Elevated HbA1c (6.2%) and FBG (118 mg/dL) require physician follow-up.",
        clinical_rule_triggered="Rule-NCD-GLY-02: FBG > 110 mg/dL with family history",
        is_acknowledged=True,
        acknowledged_by="doctor-01",
        acknowledged_at=one_week_ago,
    )

    # 27. Notification
    notification = Notification(
        recipient_user_id="citizen-ramesh-user",
        patient_id=patient.id,
        channel="IN_APP",
        title="Day 8 Care Plan Reminder",
        body="Time for your 20-minute post-dinner brisk walk! Keep up the great streak.",
    )

    # 28. Consent
    consent = Consent(
        patient_id=patient.id,
        grantee_id="doctor-01",
        grantee_role=UserRole.CLINICIAN,
        purpose="CARE_DELIVERY",
        scope_data_types=["VITALS", "LABS", "WEARABLES", "RISK_ASSESSMENTS"],
        valid_from=now,
        valid_until=now + timedelta(days=90),
    )

    # 29. Document
    doc = Document(
        patient_id=patient.id,
        file_name="nanjangud_phc_lab_report_sep2026.pdf",
        file_type="application/pdf",
        storage_path="documents/ramesh/nanjangud_phc_lab_report_sep2026.pdf",
        file_size_bytes=245100,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        uploaded_by="doctor-01",
    )

    # 30. DocumentReference
    doc_ref = DocumentReference(
        document_id=doc.id,
        patient_id=patient.id,
        doc_type="DIAGNOSTIC_LAB_REPORT",
        clinical_summary="Nanjangud PHC Diagnostic Report showing FBG 118 mg/dL and HbA1c 6.2%",
        parsed_entities_json={"hba1c": 6.2, "fasting_glucose": 118, "triglycerides": 185},
    )

    # 31. AuditEvent
    audit = AuditEvent(
        organization_id=org.id,
        actor_id="worker-01",
        actor_role=UserRole.HEALTH_WORKER,
        action=AuditAction.SCREENING_SUBMITTED,
        resource_type="Screening",
        resource_id=screening.id,
        patient_id=patient.id,
        details={"screening_type": "NCD_COMPREHENSIVE_CBAC"},
    )

    manifest = {
        "Organization": org,
        "CareTeam": care_team,
        "Patient": patient,
        "Profile": profile,
        "FamilyHistory": fam_history,
        "LifestyleProfile": lifestyle,
        "RiskFactor": risk_factors,
        "VitalSign": vitals_history,
        "LabResult": labs,
        "Medication": med,
        "MedicationAdherence": adherence_logs,
        "Screening": screening,
        "ScreeningResult": screening_result,
        "RiskAssessment": risk_assessment,
        "RiskFactorContribution": contributions,
        "RiskTrajectory": trajectory,
        "InterventionPlan": plan,
        "Intervention": interventions,
        "Goal": goals,
        "CheckIn": check_in,
        "WearableConnection": wearable_conn,
        "WearableObservation": wearable_obs,
        "ClinicalEncounter": encounter,
        "CarePlan": care_plan,
        "Referral": referral,
        "Alert": alert,
        "Notification": notification,
        "Consent": consent,
        "Document": doc,
        "DocumentReference": doc_ref,
        "AuditEvent": audit,
    }
    return manifest


def main():
    print("=" * 80)
    print("SevaHealth AI: Synthetic Domain Models Fixture Generator")
    print("=" * 80)
    dataset = build_synthetic_domain_dataset()
    print(f"[OK] Successfully instantiated all {len(dataset)} core domain entity categories:")
    for idx, (entity_name, item) in enumerate(dataset.items(), 1):
        count = len(item) if isinstance(item, list) else 1
        print(f"  {idx:2d}. {entity_name:<25} -> {count} record(s)")
    print("=" * 80)
    print("Domain model instantiation and validation successful!")


if __name__ == "__main__":
    main()
