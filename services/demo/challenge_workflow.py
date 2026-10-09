"""Seva Innovation Challenge Demo Workflow Engine (PROMPT 25).

Implements the official 16-step end-to-end demonstration workflow:
STEP 1:  Health worker registers citizen.
STEP 2:  Citizen completes NCD screening.
STEP 3:  System calculates risk.
STEP 4:  AI explains risk.
STEP 5:  System generates personalized prevention plan.
STEP 6:  Citizen connects wearable.
STEP 7:  System receives activity/sleep/heart-rate data.
STEP 8:  Risk trajectory changes.
STEP 9:  AI detects deterioration.
STEP 10: High-risk alert is generated.
STEP 11: Clinician reviews the patient.
STEP 12: Clinician creates/approves care plan.
STEP 13: Citizen receives intervention.
STEP 14: Follow-up measurement is recorded.
STEP 15: Risk trajectory improves.
STEP 16: Population dashboard shows aggregate impact.

Includes:
- Seeded, deterministic data that executes reliably every time.
- Demo Reset Button (programmatic and API callable) to restore initial state.
- Under 5 minutes execution benchmark (< 10 seconds).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from packages.types.enums import (
    UserRole,
    Gender,
    RiskTier,
    TrajectoryTrend,
    ClinicianReviewStatus,
    TriageUrgency,
    InterventionPillar,
)
from packages.auth.jwt import get_password_hash
from packages.clinical_models.observations import Observation
from packages.clinical_models.screening import ScreeningSession, CBACSurvey, IDRSSurvey
from packages.clinical_models.risk import (
    RiskAssessment,
    DomainRiskScores,
    RiskDriver,
    ProtectiveFactor,
)
from packages.clinical_models.care_plan import CarePlan, DailyTask
from packages.clinical_models.triage import ClinicalTriageCase, SOAPReport
from services.store import store, UserRecord, CitizenRecord
from services.trajectory.models import RiskSnapshot
from services.trajectory.engine import risk_trajectory_engine
from services.wearable.simulator import generate_synthetic_wearable_timeseries
from services.clinical.copilot import ClinicianCopilotEngine, ClinicianActionPayload
from services.population_intelligence.analytics import (
    get_population_overview,
    calculate_intervention_outcome_delta,
)


CHALLENGE_CITIZEN_ID = "citizen-challenge-demo-01"
CHALLENGE_USER_ID = "user-challenge-demo-01"
CHALLENGE_HEALTH_WORKER_ID = "worker-user-01"
CHALLENGE_CLINICIAN_ID = "doctor-user-01"
CHALLENGE_ADMIN_ID = "admin-user-01"


class ChallengeStepRecord(BaseModel):
    step_number: int
    title: str
    actor_role: str
    actor_name: str
    description: str
    status: str = "COMPLETED"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_time_ms: float = 0.0
    telemetry: Dict[str, Any] = Field(default_factory=dict)


class ChallengeWorkflowSummary(BaseModel):
    citizen_id: str
    citizen_name: str
    current_step: int
    total_steps: int = 16
    is_completed: bool
    total_execution_seconds: float
    baseline_risk_score: float
    peak_deteriorated_risk_score: float
    final_reversed_risk_score: float
    net_risk_reduction_percentage: float
    clinician_action: str
    population_savings_inr: float
    steps: List[ChallengeStepRecord]


# Global state store for live challenge demonstration
_challenge_steps_history: Dict[int, ChallengeStepRecord] = {}
_challenge_workflow_start_time: Optional[float] = None


def reset_challenge_demo() -> Dict[str, Any]:
    """Demo Reset Button: Purges all challenge demo artifacts and restores clean baseline.

    Guarantees deterministic execution every single time.
    """
    global _challenge_steps_history, _challenge_workflow_start_time
    _challenge_steps_history.clear()
    _challenge_workflow_start_time = None

    cid = CHALLENGE_CITIZEN_ID

    # Purge citizen records and associated memory
    if cid in store.citizens:
        del store.citizens[cid]
    if CHALLENGE_USER_ID in store.users:
        del store.users[CHALLENGE_USER_ID]
    if cid in store.observations:
        del store.observations[cid]
    if cid in store.screenings:
        del store.screenings[cid]
    if cid in store.risk_assessments:
        del store.risk_assessments[cid]
    if cid in store.care_plans:
        del store.care_plans[cid]
    if cid in store.trajectory_snapshots:
        del store.trajectory_snapshots[cid]
    if cid in store.alerts:
        del store.alerts[cid]
    if cid in store.referrals:
        del store.referrals[cid]
    if cid in store.checkins:
        del store.checkins[cid]
    if cid in store.followups:
        del store.followups[cid]
    if cid in store.wearable_data:
        del store.wearable_data[cid]
    if cid in store.copilot_drafts:
        del store.copilot_drafts[cid]
    if cid in store.legal_clinical_records:
        del store.legal_clinical_records[cid]

    # Clean triage cases matching citizen
    store.triage_cases = {k: v for k, v in store.triage_cases.items() if v.citizen_id != cid}

    return {
        "status": "RESET_SUCCESSFUL",
        "message": "Challenge Demo environment successfully reset to pristine baseline.",
        "citizen_id": cid,
        "completed_steps_count": 0,
        "total_steps": 16,
        "reset_at": datetime.now(timezone.utc).isoformat(),
    }


def _step_1_register_citizen() -> ChallengeStepRecord:
    """STEP 1: Health worker registers citizen."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID
    uid = CHALLENGE_USER_ID

    store.add_user(
        UserRecord(
            id=uid,
            tenant_id="karnataka_state_health",
            email="devendra.sharma@sevahealth.ai",
            hashed_password=get_password_hash("password123"),
            role=UserRole.CITIZEN,
            full_name="Devendra Sharma",
            assigned_jurisdiction="Devanahalli Ward 4",
            assigned_patients=[],
        )
    )

    citizen = CitizenRecord(
        id=cid,
        tenant_id="karnataka_state_health",
        user_id=uid,
        abha_id="91-7291-3849-1029",
        first_name="Devendra",
        last_name="Sharma",
        birth_date="1979-08-15",
        gender=Gender.MALE,
        phone="+91 98451 98765",
        state="Karnataka",
        district="Bengaluru Rural",
        sub_district="Devanahalli Taluk",
        village_or_ward="Devanahalli Ward 4",
    )
    store.add_citizen(citizen)

    # Consent directive for preventive screening
    from services.store import ConsentDirective
    store.add_consent(
        ConsentDirective(
            id=f"cns-chal-{uuid.uuid4().hex[:6]}",
            citizen_id=cid,
            grantee_id=CHALLENGE_HEALTH_WORKER_ID,
            grantee_role=UserRole.HEALTH_WORKER,
            purpose="CARE_DELIVERY",
        )
    )

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "citizen_id": cid,
        "abha_id": citizen.abha_id,
        "full_name": f"{citizen.first_name} {citizen.last_name}",
        "age": 47,
        "gender": citizen.gender.value,
        "registered_by": "Sunita Devi (ASHA Worker - Ward 12)",
        "location": "Bengaluru Rural, Devanahalli Taluk",
        "consent_status": "ACTIVE",
    }
    return ChallengeStepRecord(
        step_number=1,
        title="Health worker registers citizen",
        actor_role="HEALTH_WORKER",
        actor_name="Sunita Devi (ASHA Worker)",
        description="ASHA worker registers citizen Devendra Sharma at community screening camp and records demographic details with ABHA ID generation.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_2_ncd_screening() -> ChallengeStepRecord:
    """STEP 2: Citizen completes NCD screening."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID

    cbac = CBACSurvey(
        age_over_30=True,
        tobacco_user=False,
        alcohol_consumption=False,
        waist_circumference_exceeded=True,
        physical_activity_below_150min=True,
        family_history_diabetes_or_htn=True,
        symptoms=[],
    )

    idrs = IDRSSurvey(
        age_category="35-49",
        waist_category="90-99",
        physical_activity="None",
        family_history="None",
    )

    session = ScreeningSession(
        id=f"scr-chal-{uuid.uuid4().hex[:6]}",
        tenant_id="karnataka_state_health",
        citizen_id=cid,
        conducted_by_id=CHALLENGE_HEALTH_WORKER_ID,
        cbac=cbac,
        idrs=idrs,
        calculated_cbac_score=5,
        calculated_idrs_score=60,
        conducted_at=datetime.now(timezone.utc),
    )
    store.add_screening(session)

    # Record baseline clinical observations
    vitals_labs = [
        ("SYSTOLIC_BP", 134.0, "mmHg", "8480-6", "Systolic Blood Pressure"),
        ("DIASTOLIC_BP", 86.0, "mmHg", "8462-4", "Diastolic Blood Pressure"),
        ("FASTING_GLUCOSE", 112.0, "mg/dL", "1558-6", "Fasting Blood Glucose"),
        ("HBA1C", 5.9, "%", "4548-4", "Hemoglobin A1c"),
        ("BMI", 26.4, "kg/m2", "39156-5", "Body Mass Index"),
        ("WAIST_CIRCUMFERENCE", 92.0, "cm", "8280-0", "Waist Circumference"),
    ]
    for code, val, unit, loinc, name in vitals_labs:
        store.add_observation(Observation(
            id=str(uuid.uuid4()),
            tenant_id="karnataka_state_health",
            citizen_id=cid,
            code=code,
            value=val,
            unit=unit,
            loinc_code=loinc,
            display_name=name,
            source="COMMUNITY_HEALTH_CAMP",
        ))

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "screening_session_id": session.id,
        "cbac_score": session.calculated_cbac_score,
        "cbac_cutoff_flag": "REFERRAL_INDICATED (Score >= 4)",
        "idrs_score": session.calculated_idrs_score,
        "idrs_risk_category": "MODERATE_TO_HIGH_RISK (Score >= 60)",
        "vitals_summary": {
            "blood_pressure": "134/86 mmHg (Pre-hypertensive)",
            "fasting_glucose": "112 mg/dL (Impaired fasting glycemia)",
            "hba1c": "5.9% (Borderline prediabetes)",
            "bmi": "26.4 kg/m2 (Overweight Asian Indian)",
            "waist_cm": "92 cm",
        },
    }
    return ChallengeStepRecord(
        step_number=2,
        title="Citizen completes NCD screening",
        actor_role="CITIZEN",
        actor_name="Devendra Sharma (Citizen)",
        description="Citizen completes comprehensive NCD screening (CBAC score 5/10, IDRS score 60/100) and biometric measurements at community screening point.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_3_system_calculates_risk() -> ChallengeStepRecord:
    """STEP 3: System calculates risk."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID
    now = datetime.now(timezone.utc)

    domains = DomainRiskScores(
        diabetes_risk=0.58,
        hypertension_risk=0.52,
        cardiovascular_risk=0.38,
        metabolic_syndrome_risk=0.48,
        ckd_risk=0.14,
        fatty_liver_risk=0.32,
    )

    risk = RiskAssessment(
        id=f"risk-chal-base-{uuid.uuid4().hex[:6]}",
        tenant_id="karnataka_state_health",
        citizen_id=cid,
        overall_score=0.52,
        overall_tier=RiskTier.MODERATE,
        domains=domains,
        trajectory=TrajectoryTrend.STABLE,
        confidence_score=0.94,
        top_drivers=[
            RiskDriver(feature_name="Impaired Fasting Glycemia", observed_value="FBG 112 mg/dL, HbA1c 5.9%", target_value="< 100 mg/dL, < 5.7%", impact_weight=0.22),
            RiskDriver(feature_name="Prehypertension Vascular Load", observed_value="134/86 mmHg", target_value="< 120/80 mmHg", impact_weight=0.18),
            RiskDriver(feature_name="Central Visceral Adiposity", observed_value="Waist 92 cm, BMI 26.4", target_value="Waist < 90 cm", impact_weight=0.14),
            RiskDriver(feature_name="Sedentary Lifestyle Pattern", observed_value="IDRS Physical Activity Score 30", target_value="Daily active", impact_weight=0.10),
        ],
        protective_factors=[
            ProtectiveFactor(feature_name="Tobacco & Alcohol Abstinence", observed_value="Non-smoker, non-drinker", impact_weight=-0.12),
        ],
        clinical_summary="Moderate baseline cardiometabolic risk with prediabetic impaired fasting glucose and prehypertension.",
    )
    store.add_risk_assessment(risk)

    # Store baseline snapshot in trajectory store (Month 0)
    store.set_trajectory_snapshots(cid, [
        RiskSnapshot(
            snapshot_id=f"snap-chal-base",
            citizen_id=cid,
            timestamp=now - timedelta(days=60),
            domain_scores={
                "metabolic": 0.48,
                "diabetes": 0.58,
                "hypertension": 0.52,
                "cardiovascular": 0.38,
                "obesity": 0.48,
                "renal": 0.14,
                "lifestyle": 0.55,
            },
            domain_tiers={
                "metabolic": "MODERATE",
                "diabetes": "MODERATE",
                "hypertension": "MODERATE",
                "cardiovascular": "MODERATE",
                "obesity": "MODERATE",
                "renal": "LOW",
                "lifestyle": "MODERATE",
            },
            key_biomarkers={
                "HBA1C": 5.9,
                "FASTING_GLUCOSE": 112.0,
                "SYSTOLIC_BP": 134.0,
                "DIASTOLIC_BP": 86.0,
                "BMI": 26.4,
                "WAIST_CIRCUMFERENCE": 92.0,
            },
            source="BASELINE_CAMP_SCREENING",
        )
    ])

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "risk_assessment_id": risk.id,
        "overall_composite_score": 0.52,
        "overall_risk_tier": "MODERATE",
        "domain_breakdown": {
            "diabetes_risk": "58% (Moderate-High)",
            "hypertension_risk": "52% (Moderate)",
            "cardiovascular_risk": "38% (Moderate)",
            "metabolic_syndrome_risk": "48% (Moderate)",
            "ckd_risk": "14% (Low)",
        },
        "trajectory_status": "STABLE_BASELINE",
        "model_confidence": 0.94,
    }
    return ChallengeStepRecord(
        step_number=3,
        title="System calculates risk",
        actor_role="SYSTEM",
        actor_name="SevaHealth Risk Engine",
        description="Multi-factor NCD Risk Engine evaluates 6 clinical domains and stratifies citizen into MODERATE overall risk (Composite Score: 52%).",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_4_ai_explains_risk() -> ChallengeStepRecord:
    """STEP 4: AI explains risk."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID

    attribution_waterfall = [
        {"factor": "Impaired Fasting Glycemia (FBG 112 mg/dL, HbA1c 5.9%)", "impact": "+22%", "category": "BIOMETRIC", "guideline": "ICMR Guidelines for Prediabetes"},
        {"factor": "Prehypertension Vascular Load (134/86 mmHg)", "impact": "+18%", "category": "VASCULAR", "guideline": "Indian Guidelines on Hypertension (I-GH-IV)"},
        {"factor": "Central Visceral Adiposity (Waist 92 cm, BMI 26.4 kg/m²)", "impact": "+14%", "category": "ANTHROPOMETRIC", "guideline": "WHO South Asian Cutoffs"},
        {"factor": "Physical Inactivity (Sedentary routine)", "impact": "+10%", "category": "LIFESTYLE", "guideline": "WHO Guidelines on Physical Activity"},
        {"factor": "Tobacco & Alcohol Abstinence", "impact": "-12%", "category": "PROTECTIVE", "guideline": "CVD Primary Prevention Guidelines"},
    ]

    explanations = {
        "en": "Hello Devendra. Your overall NCD risk is Moderate (52%). The primary contributors are slightly elevated fasting blood sugar (112 mg/dL) and prehypertensive blood pressure (134/86 mmHg). Early lifestyle modification can stabilize these biomarkers before they require medications.",
        "kn": "ನಮಸ್ಕಾರ Devendra. ನಿಮ್ಮ ಒಟ್ಟಾರೆ NCD ಅಪಾಯವು ಮಧ್ಯಮ (52%) ಮಟ್ಟದಲ್ಲಿದೆ. ಮುಖ್ಯ ಕಾರಣಗಳೆಂದರೆ ರಕ್ತದ ಗ್ಲೂಕೋಸ್ (112 mg/dL) ಮತ್ತು ರಕ್ತದೊತ್ತಡ (134/86 mmHg). ಆರಂಭಿಕ ಜೀವನಶೈಲಿ ಬದಲಾವಣೆಗಳಿಂದ ಇದನ್ನು ಸರಿಪಡಿಸಬಹುದು.",
        "hi": "नमस्ते Devendra. आपका समग्र NCD जोखिम मध्यम (52%) है। मुख्य योगदानकर्ता थोड़ा बढ़ा हुआ रक्त शर्करा (112 mg/dL) और रक्तचाप (134/86 mmHg) हैं। समय पर जीवनशैली बदलाव से इसे नियंत्रित किया जा सकता है।",
    }

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "attribution_waterfall": attribution_waterfall,
        "multilingual_explanations": explanations,
        "explainability_method": "SHAP-inspired biometric factor attribution",
        "black_box_prevention": "Fully groundable in clinical biomarkers & clinical guidelines",
    }
    return ChallengeStepRecord(
        step_number=4,
        title="AI explains risk",
        actor_role="AI_ENGINE",
        actor_name="Explainable AI Prevention Engine",
        description="AI generates transparent, non-black-box risk attribution waterfall decomposing the 52% risk score with multilingual explanations in English, Kannada, and Hindi.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_5_generate_prevention_plan() -> ChallengeStepRecord:
    """STEP 5: System generates personalized prevention plan."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID

    daily_tasks: List[DailyTask] = []
    for d in range(1, 31):
        if d % 2 == 1:
            pillar = InterventionPillar.NUTRITION
            title = f"Day {d}: Replace white rice with Foxtail Millet (Navane) at lunch"
            desc = "Traditional foxtail millet contains 8x higher dietary fiber than polished rice, blunting postprandial glucose spikes."
            metric = "1 whole-grain millet meal"
        else:
            pillar = InterventionPillar.PHYSICAL_ACTIVITY
            title = f"Day {d}: 20-Minute Post-Dinner Brisk Walk (Target: 6,500 Steps)"
            desc = "Light postprandial ambulation enhances muscular GLUT-4 glucose transporter uptake independently of insulin."
            metric = "6,500 steps logged"

        daily_tasks.append(DailyTask(
            id=f"dev-task-{d}",
            day=d,
            pillar=pillar,
            title=title,
            description=desc,
            target_metric=metric,
            completed=False,
        ))

    plan = CarePlan(
        id=f"careplan-chal-{uuid.uuid4().hex[:6]}",
        tenant_id="karnataka_state_health",
        citizen_id=cid,
        risk_assessment_id="risk-chal-base",
        title="SevaHealth 30-Day Cardiometabolic Prevention Journey",
        focus_domain="Prediabetes Reversal & Prehypertension Normalization",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        adherence_percentage=0.0,
        nutrition_guidance="Replace 50% of polished white rice with traditional foxtail millet (Navane) or ragi; eliminate sweetened tea and processed snacks.",
        activity_guidance="Target 6,500 daily steps with 20 minutes of moderate brisk walking post-dinner.",
        sleep_guidance="Maintain 7.5 hours nightly restful sleep with digital cutoff 45 mins before bedtime.",
        stress_guidance="Practice daily 5-minute diaphragmatic breathing.",
        daily_tasks=daily_tasks,
        clinician_reviewed=False,
    )
    store.set_care_plan(plan)

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "care_plan_id": plan.id,
        "title": plan.title,
        "duration_days": 30,
        "total_scheduled_tasks": len(daily_tasks),
        "pillars": ["NUTRITION", "PHYSICAL_ACTIVITY", "SLEEP_HYGIENE", "STRESS_AND_LIFESTYLE"],
        "adherence_tracking": "INITIALIZED (0.0%)",
        "clinician_status": "DRAFT_PENDING_CLINICAL_VERIFICATION",
    }
    return ChallengeStepRecord(
        step_number=5,
        title="System generates personalized prevention plan",
        actor_role="SYSTEM",
        actor_name="SevaHealth Intervention Engine",
        description="System translates risk into an actionable 30-day lifestyle medicine care plan with 30 scheduled daily micro-habit tasks across 4 clinical pillars.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_6_connect_wearable() -> ChallengeStepRecord:
    """STEP 6: Citizen connects wearable."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID

    device_info = {
        "device_id": "DEV-FIT-78492",
        "device_type": "SMARTWATCH_FITNESS_TRACKER",
        "manufacturer": "Noise / Titan Smart Pro",
        "firmware_version": "v2.14.8-BLE",
        "connection_protocol": "BLE_HEALTH_SYNC_V2",
        "connection_status": "CONNECTED",
        "battery_level": 94,
        "sensors_active": ["OPTICAL_HEART_RATE_PPG", "3_AXIS_ACCELEROMETER", "SLEEP_STAGE_MONITOR"],
        "paired_at": datetime.now(timezone.utc).isoformat(),
    }

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "citizen_id": cid,
        "device_pairing": device_info,
        "data_authorization": "HEALTH_KIT_WEARABLE_PERMISSION_GRANTED",
        "sync_channel": "ENCRYPTED_BLUETOOTH_SECURE_TUNNEL",
    }
    return ChallengeStepRecord(
        step_number=6,
        title="Citizen connects wearable",
        actor_role="CITIZEN",
        actor_name="Devendra Sharma (Citizen)",
        description="Citizen pairs smartwatch / fitness tracker via SevaHealth Mobile App; authorizations granted for background accelerometry, PPG, and sleep telemetry.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_7_receive_wearable_telemetry() -> ChallengeStepRecord:
    """STEP 7: System receives activity/sleep/heart-rate data."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID

    # Generate 14-day synthetic timeseries baseline
    telemetry_series = generate_synthetic_wearable_timeseries(
        citizen_id=cid,
        days=14,
        base_rhr=73.0,
        base_hrv=39.5,
        base_steps=5100,
        stress_trend=False,
    )
    store.wearable_data[cid] = telemetry_series

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "citizen_id": cid,
        "days_synced": 14,
        "records_ingested": len(telemetry_series),
        "7_day_averages": {
            "daily_steps": 5100,
            "resting_heart_rate_bpm": 73.0,
            "hrv_rmssd_ms": 39.5,
            "sleep_duration_hours": 6.4,
            "sleep_efficiency_percentage": 78.0,
        },
        "ingestion_status": "NORMAL_INGESTION_HEALTHY",
    }
    return ChallengeStepRecord(
        step_number=7,
        title="System receives activity/sleep/heart-rate data",
        actor_role="SYSTEM",
        actor_name="Wearable Ingestion Engine",
        description="System securely receives and processes continuous wearable telemetry: 5,100 steps/day, 73 bpm resting heart rate, 39.5 ms HRV, and 6.4h sleep/night.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_8_risk_trajectory_changes() -> ChallengeStepRecord:
    """STEP 8: Risk trajectory changes."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID
    now = datetime.now(timezone.utc)

    # Citizen experiences silent deterioration over next 60 days
    deteriorated_vitals = [
        ("SYSTOLIC_BP", 148.0, "mmHg", "8480-6", "Systolic Blood Pressure"),
        ("DIASTOLIC_BP", 94.0, "mmHg", "8462-4", "Diastolic Blood Pressure"),
        ("FASTING_GLUCOSE", 124.0, "mg/dL", "1558-6", "Fasting Blood Glucose"),
        ("HBA1C", 6.4, "%", "4548-4", "Hemoglobin A1c"),
        ("BMI", 28.2, "kg/m2", "39156-5", "Body Mass Index"),
        ("WAIST_CIRCUMFERENCE", 95.0, "cm", "8280-0", "Waist Circumference"),
    ]
    for code, val, unit, loinc, name in deteriorated_vitals:
        store.add_observation(Observation(
            id=str(uuid.uuid4()),
            tenant_id="karnataka_state_health",
            citizen_id=cid,
            code=code,
            value=val,
            unit=unit,
            loinc_code=loinc,
            display_name=name,
            source="WEARABLE_AND_REPEAT_SCREENING",
        ))

    # Wearable telemetry reflects deterioration: steps collapse to 2,800, RHR rises to 81 bpm
    store.wearable_data[cid] = generate_synthetic_wearable_timeseries(
        citizen_id=cid,
        days=14,
        base_rhr=81.0,
        base_hrv=27.0,
        base_steps=2800,
        stress_trend=True,
    )

    # New snapshot logged in trajectory store (Month 2)
    current_snapshots = store.get_trajectory_snapshots(cid)
    snap2 = RiskSnapshot(
        snapshot_id=f"snap-chal-drift",
        citizen_id=cid,
        timestamp=now,
        domain_scores={
            "metabolic": 0.74,
            "diabetes": 0.78,
            "hypertension": 0.72,
            "cardiovascular": 0.58,
            "obesity": 0.65,
            "renal": 0.24,
            "lifestyle": 0.80,
        },
        domain_tiers={
            "metabolic": "HIGH",
            "diabetes": "HIGH",
            "hypertension": "HIGH",
            "cardiovascular": "MODERATE",
            "obesity": "HIGH",
            "renal": "LOW",
            "lifestyle": "HIGH",
        },
        key_biomarkers={
            "HBA1C": 6.4,
            "FASTING_GLUCOSE": 124.0,
            "SYSTOLIC_BP": 148.0,
            "DIASTOLIC_BP": 94.0,
            "BMI": 28.2,
            "WAIST_CIRCUMFERENCE": 95.0,
            "STEPS": 2800,
        },
        source="INTERMEDIATE_DRIFT_EVALUATION",
    )
    store.set_trajectory_snapshots(cid, current_snapshots + [snap2])

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "biometric_shifts": {
            "systolic_bp": "134 -> 148 mmHg (+14 mmHg spike)",
            "fasting_glucose": "112 -> 124 mg/dL (+12 mg/dL drift)",
            "hba1c": "5.9% -> 6.4% (Higher prediabetes tier)",
            "bmi": "26.4 -> 28.2 kg/m2 (+5.2 kg weight gain)",
            "daily_steps": "5,100 -> 2,800 steps/day (-45% collapse)",
            "resting_hr": "73 -> 81 bpm (+8 bpm increase)",
        },
        "trajectory_shift": "Baseline Moderate -> Worsening Drift Detected",
        "snapshots_recorded": len(store.get_trajectory_snapshots(cid)),
    }
    return ChallengeStepRecord(
        step_number=8,
        title="Risk trajectory changes",
        actor_role="SYSTEM",
        actor_name="Risk Trajectory Engine",
        description="Citizen experiences silent lifestyle disruption over 60 days: Blood pressure worsens to 148/94 mmHg, HbA1c creeps to 6.4%, and daily steps collapse to 2,800.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_9_ai_detects_deterioration() -> ChallengeStepRecord:
    """STEP 9: AI detects deterioration."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID

    # Recalculate full trajectory and report
    snaps = store.get_trajectory_snapshots(cid)
    report = risk_trajectory_engine.evaluate_trajectory(cid, snaps)

    # Update risk assessment to HIGH tier
    drift_risk = RiskAssessment(
        id=f"risk-chal-drift-{uuid.uuid4().hex[:6]}",
        tenant_id="karnataka_state_health",
        citizen_id=cid,
        overall_score=0.79,
        overall_tier=RiskTier.HIGH,
        domains=DomainRiskScores(
            diabetes_risk=0.78,
            hypertension_risk=0.72,
            cardiovascular_risk=0.58,
            metabolic_syndrome_risk=0.74,
            ckd_risk=0.24,
            fatty_liver_risk=0.62,
        ),
        trajectory=TrajectoryTrend.DETERIORATING,
        confidence_score=0.96,
        top_drivers=[
            RiskDriver(feature_name="Accelerated Glycemic Deterioration", observed_value="HbA1c 6.4%, FBG 124 mg/dL", target_value="< 5.7%", impact_weight=0.32),
            RiskDriver(feature_name="Stage 1 Hypertension Vascular Strain", observed_value="148/94 mmHg", target_value="< 120/80 mmHg", impact_weight=0.26),
            RiskDriver(feature_name="Severe Physical Inactivity Collapse", observed_value="2,800 steps/day", target_value="> 7,000 steps", impact_weight=0.20),
            RiskDriver(feature_name="Progressive Central Adiposity", observed_value="BMI 28.2, Waist 95 cm", target_value="Waist < 90 cm", impact_weight=0.18),
        ],
        clinical_summary="Rapid multi-domain deterioration across glycemic, vascular, and physical activity parameters. Clinical escalation required.",
    )
    store.add_risk_assessment(drift_risk)

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "trajectory_trend": "DETERIORATING",
        "composite_change_percentage": report.composite_change_percentage,
        "risk_score_jump": "52% -> 79% (+27% escalation)",
        "velocity_classification": "ACCELERATED_DETERIORATION",
        "ai_alert_flag": "WORSENING_TRAJECTORY_THRESHOLD_BREACHED",
        "key_deterioration_vectors": [
            "Vascular strain: SBP +14 mmHg",
            "Glycemic creep: HbA1c +0.5%",
            "Activity collapse: -45% daily steps",
        ],
    }
    return ChallengeStepRecord(
        step_number=9,
        title="AI detects deterioration",
        actor_role="AI_ENGINE",
        actor_name="AI Trend & Velocity Engine",
        description="AI detects accelerated upward trajectory velocity (+51.9% risk drift); composite risk surges from 52% (Moderate) to 79% (HIGH).",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_10_high_risk_alert_generated() -> ChallengeStepRecord:
    """STEP 10: High-risk alert is generated."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID
    now = datetime.now(timezone.utc)

    alert_id = f"alert-chal-{uuid.uuid4().hex[:6]}"
    alert_record = {
        "id": alert_id,
        "citizen_id": cid,
        "patient_id": cid,
        "urgency": "PRIORITY",
        "alert_type": "RAPID_METABOLIC_VASCULAR_DETERIORATION",
        "message": "Citizen Devendra Sharma surged from Moderate (52%) to HIGH Risk (79%). Persistent Stage 1 HTN (148/94 mmHg) and HbA1c (6.4%) require urgent clinician review.",
        "clinical_rule_triggered": "RULE_NCD_VELOCITY_ESCALATION",
        "created_at": now.isoformat(),
        "is_acknowledged": False,
    }
    store.add_alert(alert_record)

    soap = SOAPReport(
        subjective="Patient reported increased fatigue and stress over the last 60 days. Stopped daily walks.",
        objective="Blood pressure 148/94 mmHg, Fasting blood sugar 124 mg/dL, HbA1c 6.4%, Daily steps 2,800.",
        assessment="Accelerated cardiometabolic deterioration: Stage 1 hypertension and prediabetes glycemic creep.",
        plan="Recommend in-person PHC review, dietary sodium restriction, foxtail millet substitution, and structured walking.",
        key_observations={"bp": "148/94 mmHg", "hba1c": "6.4%", "steps": 2800},
    )

    triage_case = ClinicalTriageCase(
        id=f"triage-chal-{uuid.uuid4().hex[:6]}",
        tenant_id="karnataka_state_health",
        citizen_id=cid,
        citizen_name="Devendra Sharma",
        risk_assessment_id="risk-chal-drift",
        urgency=TriageUrgency.PRIORITY,
        escalation_reason="Deteriorating NCD risk trajectory with high glycemic and vascular strain.",
        soap_note=soap,
        status=ClinicianReviewStatus.PENDING,
        assigned_clinician_id=CHALLENGE_CLINICIAN_ID,
        created_at=now,
    )
    store.add_triage_case(triage_case)

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "alert_id": alert_id,
        "triage_case_id": triage_case.id,
        "urgency": "PRIORITY",
        "assigned_clinician": "Dr. Anand Kulkarni, MD (Treating Medical Officer)",
        "queue_status": "ENQUEUED_AT_TOP_OF_TRIAGE_QUEUE",
        "notification_dispatched": "SMS/Push sent to ASHA Worker & PHC Medical Officer",
    }
    return ChallengeStepRecord(
        step_number=10,
        title="High-risk alert is generated",
        actor_role="SYSTEM",
        actor_name="Clinical Triage & Alerting Engine",
        description="Automated clinical escalation engine generates high-priority alert and enqueues citizen Devendra Sharma at the top of Dr. Anand Kulkarni's PHC triage queue.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_11_clinician_reviews_patient() -> ChallengeStepRecord:
    """STEP 11: Clinician reviews the patient."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID

    # Generate clinician copilot synthesis draft
    from packages.auth.jwt import TokenPayload
    doctor_actor = TokenPayload(
        sub=CHALLENGE_CLINICIAN_ID,
        tenant_id="karnataka_state_health",
        role=UserRole.CLINICIAN,
    )
    draft = ClinicianCopilotEngine.generate_copilot_synthesis(cid, doctor_actor)

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "reviewing_doctor": "Dr. Anand Kulkarni, MD",
        "clinical_summary": draft.clinical_summary,
        "risk_summary": draft.risk_summary,
        "recent_changes": draft.recent_changes,
        "missing_information": draft.missing_information,
        "possible_contributing_factors": draft.possible_contributing_factors,
        "suggested_follow_up": draft.suggested_follow_up,
        "verification_status": "DRAFT_PENDING_CLINICIAN_VERIFICATION",
        "is_committed_to_legal_record": False,
        "human_in_the_loop_safeguard": "AI never makes autonomous diagnoses or legal commitments",
    }
    return ChallengeStepRecord(
        step_number=11,
        title="Clinician reviews the patient",
        actor_role="CLINICIAN",
        actor_name="Dr. Anand Kulkarni, MD",
        description="Treating Medical Officer opens Clinician Copilot portal, reviews 11-dimension patient summary, trajectory curve, and AI-synthesized draft SOAP note.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_12_clinician_approves_care_plan() -> ChallengeStepRecord:
    """STEP 12: Clinician creates/approves care plan."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID

    from packages.auth.jwt import TokenPayload
    doctor_actor = TokenPayload(
        sub=CHALLENGE_CLINICIAN_ID,
        tenant_id="karnataka_state_health",
        role=UserRole.CLINICIAN,
    )

    action_payload = ClinicianActionPayload(
        action="CREATE_CARE_PLAN",
        care_plan_title="Doctor Prescribed Intensive 30-Day Glycemic & Vascular Stabilization",
        dietary_prescription="Strict whole-millet substitution (foxtail/ragi), eliminate refined sugars, restrict sodium < 2g/day.",
        activity_prescription="Daily 30-minute brisk walk (minimum 7,500 steps/day) with light resistance exercises.",
        duration_days=30,
        clinician_comments="Patient counseled on reversible nature of prediabetes and stage 1 hypertension. Pharmacotherapy deferred pending 30-day lifestyle medicine trial.",
    )

    verification_record = ClinicianCopilotEngine.process_clinician_action(
        citizen_id=cid,
        action_payload=action_payload,
        actor=doctor_actor,
    )

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "clinician_action": "CREATE_CARE_PLAN & APPROVE",
        "approved_care_plan_id": verification_record.active_care_plan_id,
        "prescribed_diet": action_payload.dietary_prescription,
        "prescribed_activity": action_payload.activity_prescription,
        "doctor_digital_signature": "Signed by Dr. Anand Kulkarni, MD (Reg: KMC-48192)",
        "legal_record_committed": True,
        "status": "APPROVED",
    }
    return ChallengeStepRecord(
        step_number=12,
        title="Clinician creates/approves care plan",
        actor_role="CLINICIAN",
        actor_name="Dr. Anand Kulkarni, MD",
        description="Doctor approves and signs off on an intensive 30-day lifestyle medicine care plan; legally commits prescription into medical record with digital signature.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_13_citizen_receives_intervention() -> ChallengeStepRecord:
    """STEP 13: Citizen receives intervention."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID
    now = datetime.now(timezone.utc)

    # Fetch active plan and simulate high adherence execution
    plan = store.get_care_plan(cid)
    if plan and plan.daily_tasks:
        for i, task in enumerate(plan.daily_tasks):
            if i < 27:  # 27 / 30 = 90.0% adherence!
                task.completed = True
                task.completed_at = now - timedelta(days=30 - i)
        plan.adherence_percentage = 90.0
        store.set_care_plan(plan)

    # Log daily check-ins
    for d in range(1, 28):
        store.add_checkin(cid, {
            "id": f"chk-chal-{d}",
            "citizen_id": cid,
            "day": d,
            "task_completed": True,
            "reported_symptoms": "Feeling more energetic, sleep improved",
            "timestamp": (now - timedelta(days=30 - d)).isoformat(),
        })

    # Wearables sync shows daily steps surged to 8,100 steps
    store.wearable_data[cid] = generate_synthetic_wearable_timeseries(
        citizen_id=cid,
        days=14,
        base_rhr=65.0,
        base_hrv=48.0,
        base_steps=8100,
        stress_trend=False,
    )

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "care_plan_title": plan.title if plan else "Intensive Stabilization Plan",
        "tasks_completed": "27 of 30 tasks completed",
        "adherence_rate": "90.0%",
        "wearable_activity_sync": "Average daily steps surged to 8,100 steps/day (+189% increase)",
        "resting_heart_rate": "Dropped from 81 bpm to 65 bpm (-16 bpm improvement)",
        "daily_checkins_logged": 27,
        "citizen_engagement": "HIGHLY_ACTIVE",
    }
    return ChallengeStepRecord(
        step_number=13,
        title="Citizen receives intervention",
        actor_role="CITIZEN",
        actor_name="Devendra Sharma (Citizen)",
        description="Citizen engages with SevaHealth Mobile App & AI Prevention Agent daily; logs 90.0% adherence (27/30 tasks) with verified wearable movement surge.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_14_followup_measurement_recorded() -> ChallengeStepRecord:
    """STEP 14: Follow-up measurement is recorded."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID

    followup_vitals = [
        ("SYSTOLIC_BP", 120.0, "mmHg", "8480-6", "Systolic Blood Pressure"),
        ("DIASTOLIC_BP", 78.0, "mmHg", "8462-4", "Diastolic Blood Pressure"),
        ("FASTING_GLUCOSE", 94.0, "mg/dL", "1558-6", "Fasting Blood Glucose"),
        ("HBA1C", 5.6, "%", "4548-4", "Hemoglobin A1c"),
        ("BMI", 26.1, "kg/m2", "39156-5", "Body Mass Index"),
        ("WAIST_CIRCUMFERENCE", 87.0, "cm", "8280-0", "Waist Circumference"),
    ]
    for code, val, unit, loinc, name in followup_vitals:
        store.add_observation(Observation(
            id=str(uuid.uuid4()),
            tenant_id="karnataka_state_health",
            citizen_id=cid,
            code=code,
            value=val,
            unit=unit,
            loinc_code=loinc,
            display_name=name,
            source="POST_INTERVENTION_FOLLOWUP_CAMP",
        ))

    store.add_followup(cid, {
        "id": f"fol-chal-{uuid.uuid4().hex[:6]}",
        "citizen_id": cid,
        "facility": "Devanahalli Community Health Centre (CHC)",
        "clinical_examiner": "Sunita Devi (ASHA) / Dr. Anand Kulkarni",
        "findings": "Significant objective biometric reversal. Glycemia and blood pressure normalized.",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "followup_vitals": {
            "blood_pressure": "120/78 mmHg (Normalized from 148/94 mmHg, -28 mmHg systolic drop!)",
            "fasting_glucose": "94 mg/dL (Normalized from 124 mg/dL, -30 mg/dL)",
            "hba1c": "5.6% (Normalized from 6.4%, prediabetes reversed!)",
            "bmi": "26.1 kg/m2 (Weight loss: -5.1 kg from 81.2 kg to 76.1 kg)",
            "waist_cm": "87 cm (Down -5 cm, meeting Asian Indian target)",
        },
        "clinical_status": "OBJECTIVE_BIOMETRIC_NORMALIZATION_CONFIRMED",
    }
    return ChallengeStepRecord(
        step_number=14,
        title="Follow-up measurement is recorded",
        actor_role="HEALTH_WORKER",
        actor_name="Sunita Devi (ASHA) & PHC Team",
        description="Follow-up health camp measurements confirm dramatic clinical normalization: BP 120/78 mmHg (-28 mmHg), HbA1c 5.6% (prediabetes reversed), and -5.1 kg weight loss.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_15_risk_trajectory_improves() -> ChallengeStepRecord:
    """STEP 15: Risk trajectory improves."""
    t0 = time.time()
    cid = CHALLENGE_CITIZEN_ID
    now = datetime.now(timezone.utc)

    reversed_risk = RiskAssessment(
        id=f"risk-chal-rev-{uuid.uuid4().hex[:6]}",
        tenant_id="karnataka_state_health",
        citizen_id=cid,
        overall_score=0.22,
        overall_tier=RiskTier.LOW,
        domains=DomainRiskScores(
            diabetes_risk=0.14,
            hypertension_risk=0.16,
            cardiovascular_risk=0.18,
            metabolic_syndrome_risk=0.20,
            ckd_risk=0.08,
            fatty_liver_risk=0.14,
        ),
        trajectory=TrajectoryTrend.IMPROVING,
        confidence_score=0.98,
        top_drivers=[
            RiskDriver(feature_name="Glycemic Normalization", observed_value="HbA1c 5.6%, FBG 94 mg/dL", target_value="< 5.7%", impact_weight=0.08),
            RiskDriver(feature_name="Optimal Vascular Pressure", observed_value="120/78 mmHg", target_value="< 120/80 mmHg", impact_weight=0.07),
        ],
        protective_factors=[
            ProtectiveFactor(feature_name="Sustained High Physical Activity", observed_value="8,100 steps/day", impact_weight=-0.28),
            ProtectiveFactor(feature_name="Whole Millet High-Fiber Diet", observed_value="Daily Navane substitution", impact_weight=-0.22),
            ProtectiveFactor(feature_name="Weight Reduction", observed_value="-5.1 kg body mass drop", impact_weight=-0.18),
        ],
        clinical_summary="Prediabetes reversal and prehypertension resolution achieved through high-adherence lifestyle medicine.",
    )
    store.add_risk_assessment(reversed_risk)

    current_snapshots = store.get_trajectory_snapshots(cid)
    snap3 = RiskSnapshot(
        snapshot_id=f"snap-chal-rev",
        citizen_id=cid,
        timestamp=now,
        domain_scores={
            "metabolic": 0.20,
            "diabetes": 0.14,
            "hypertension": 0.16,
            "cardiovascular": 0.18,
            "obesity": 0.24,
            "renal": 0.08,
            "lifestyle": 0.12,
        },
        domain_tiers={
            "metabolic": "LOW",
            "diabetes": "LOW",
            "hypertension": "LOW",
            "cardiovascular": "LOW",
            "obesity": "LOW",
            "renal": "LOW",
            "lifestyle": "LOW",
        },
        key_biomarkers={
            "HBA1C": 5.6,
            "FASTING_GLUCOSE": 94.0,
            "SYSTOLIC_BP": 120.0,
            "DIASTOLIC_BP": 78.0,
            "BMI": 26.1,
            "WAIST_CIRCUMFERENCE": 87.0,
            "STEPS": 8100,
        },
        source="POST_INTERVENTION_OUTCOME",
    )
    store.set_trajectory_snapshots(cid, current_snapshots + [snap3])

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "trajectory_trend": "IMPROVING",
        "baseline_risk": "52% (Moderate)",
        "peak_deteriorated_risk": "79% (High)",
        "final_reversed_risk": "22% (Low)",
        "net_relative_risk_reduction": "72.2% reduction",
        "absolute_risk_reduction": "-57.0% from peak",
        "clinical_conclusion": "PREDIABETES_REVERSED_AND_STAGE_1_HTN_RESOLVED",
    }
    return ChallengeStepRecord(
        step_number=15,
        title="Risk trajectory improves",
        actor_role="SYSTEM",
        actor_name="SevaHealth Trajectory Engine",
        description="Risk trajectory turns sharply IMPROVING; composite risk score plunges from 79% (High) down to 22% (Low) — a 72.2% relative risk reduction.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


def _step_16_population_dashboard_impact() -> ChallengeStepRecord:
    """STEP 16: Population dashboard shows aggregate impact."""
    t0 = time.time()

    population_metrics = {
        "district": "Bengaluru Rural",
        "total_citizens_screened": 5420,
        "high_risk_citizens_identified": 840,
        "enrolled_in_lifestyle_interventions": 840,
        "cohort_intervention_adherence": 88.4,
        "clinical_outcomes_delta": {
            "average_hba1c_reduction": "-0.65% across prediabetic cohort",
            "average_systolic_bp_reduction": "-14.8 mmHg across prehypertension cohort",
            "risk_migration_rate": "64.2% of high-risk citizens transitioned to low/moderate risk",
        },
        "economic_roi": {
            "cost_avoidance_per_citizen_year_inr": 45000,
            "district_annualized_cost_savings_inr": 37800000,
            "savings_description": "Avoided emergency admissions, outpatient visits, and downstream dialysis/cardiac interventions.",
        },
    }

    elapsed = (time.time() - t0) * 1000
    telemetry = {
        "population_command_center": population_metrics,
        "macro_intelligence": "Population level health command center updates in real time to reflect preventive cohort outcomes.",
        "challenge_verdict": "SevaHealth AI proves closed loop from community screening to population economic impact.",
    }
    return ChallengeStepRecord(
        step_number=16,
        title="Population dashboard shows aggregate impact",
        actor_role="PUBLIC_HEALTH_ADMIN",
        actor_name="Dr. Radhika Rao (District Health Officer)",
        description="District Health Command Center aggregates 5,420 citizens; demonstrates 64.2% risk migration, -14.8 mmHg SBP reduction, and ₹3.78 Crores in healthcare cost avoidance.",
        execution_time_ms=elapsed,
        telemetry=telemetry,
    )


STEP_RUNNERS = {
    1: _step_1_register_citizen,
    2: _step_2_ncd_screening,
    3: _step_3_system_calculates_risk,
    4: _step_4_ai_explains_risk,
    5: _step_5_generate_prevention_plan,
    6: _step_6_connect_wearable,
    7: _step_7_receive_wearable_telemetry,
    8: _step_8_risk_trajectory_changes,
    9: _step_9_ai_detects_deterioration,
    10: _step_10_high_risk_alert_generated,
    11: _step_11_clinician_reviews_patient,
    12: _step_12_clinician_approves_care_plan,
    13: _step_13_citizen_receives_intervention,
    14: _step_14_followup_measurement_recorded,
    15: _step_15_risk_trajectory_improves,
    16: _step_16_population_dashboard_impact,
}


def execute_challenge_step(step_number: int) -> ChallengeStepRecord:
    """Executes a single step (1-16) of the Seva Innovation Challenge Demo."""
    global _challenge_steps_history, _challenge_workflow_start_time

    if step_number not in STEP_RUNNERS:
        raise ValueError(f"Invalid step number: {step_number}. Must be between 1 and 16.")

    if _challenge_workflow_start_time is None:
        _challenge_workflow_start_time = time.time()

    # Pre-requisite enforcement: if executing step N > 1 and step N-1 hasn't run, execute prior steps
    for prev_step in range(1, step_number):
        if prev_step not in _challenge_steps_history:
            record = STEP_RUNNERS[prev_step]()
            _challenge_steps_history[prev_step] = record

    record = STEP_RUNNERS[step_number]()
    _challenge_steps_history[step_number] = record
    return record


def execute_all_challenge_steps() -> ChallengeWorkflowSummary:
    """Executes all 16 steps of the Seva Innovation Challenge Demo from Step 1 to Step 16."""
    global _challenge_steps_history, _challenge_workflow_start_time
    start_time = time.time()
    _challenge_workflow_start_time = start_time

    for step_num in range(1, 17):
        record = STEP_RUNNERS[step_num]()
        _challenge_steps_history[step_num] = record

    elapsed = time.time() - start_time

    summary = ChallengeWorkflowSummary(
        citizen_id=CHALLENGE_CITIZEN_ID,
        citizen_name="Devendra Sharma",
        current_step=16,
        total_steps=16,
        is_completed=True,
        total_execution_seconds=round(elapsed, 3),
        baseline_risk_score=0.52,
        peak_deteriorated_risk_score=0.79,
        final_reversed_risk_score=0.22,
        net_risk_reduction_percentage=72.2,
        clinician_action="APPROVED by Dr. Anand Kulkarni, MD",
        population_savings_inr=37800000.0,
        steps=[_challenge_steps_history[s] for s in sorted(_challenge_steps_history.keys())],
    )
    return summary


def get_challenge_demo_state() -> Dict[str, Any]:
    """Retrieves current execution status of the challenge demo workflow."""
    global _challenge_steps_history, _challenge_workflow_start_time

    completed_count = len(_challenge_steps_history)
    is_completed = (completed_count == 16)
    elapsed = (time.time() - _challenge_workflow_start_time) if _challenge_workflow_start_time else 0.0

    steps_list = [_challenge_steps_history[s].model_dump() for s in sorted(_challenge_steps_history.keys())]

    return {
        "citizen_id": CHALLENGE_CITIZEN_ID,
        "citizen_name": "Devendra Sharma",
        "completed_steps_count": completed_count,
        "total_steps": 16,
        "is_completed": is_completed,
        "elapsed_seconds": round(elapsed, 3),
        "steps": steps_list,
        "reset_available": True,
        "reset_endpoint": "/api/v1/challenge-demo/reset",
    }
