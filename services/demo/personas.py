"""SevaHealth AI Synthetic Personas Generator.

Creates 12 comprehensive synthetic personas representing diverse epidemiological
profiles across India:
1. Healthy / Low Risk (Priya Sharma)
2. Prediabetes (Ramesh Patel)
3. Newly Detected Hypertension Risk (Suresh Kumar)
4. Obesity / Metabolic Syndrome (Anita Desai)
5. High Cardiovascular Risk (Vikram Singh)
6. Improving Citizen (Meera Bai)
7. Deteriorating Citizen (Rajesh Verma)
8. Elderly High-Risk Citizen (Lakshmi Devi)
9. Sedentary Young Adult (Rohan Nair)
10. Multiple-Risk Citizen (Gurpreet Kaur)
11. Story Hero Persona (Arjun Mehta)
12. Rural Community Field Screened Mother (Fatima Bi)

Generates complete clinical records:
- Labs & Vitals (with LOINC codes)
- Wearables (smartwatch timeseries)
- Screenings (CBAC & IDRS)
- Risk Assessments & SHAP-style attribution drivers
- Longitudinal Risk Trajectories
- 30-Day Prevention Care Plans (interventions)
- Daily Check-ins
- Clinical Alerts
- Referrals & Triage Cases

DISCLAIMER: Synthetic demonstration data for research and platform validation.
Not clinically validated.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from packages.types.enums import (
    UserRole,
    Gender,
    RiskTier,
    TrajectoryTrend,
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
from services.wearable.simulator import generate_synthetic_wearable_timeseries
from services.trajectory.models import RiskSnapshot


class PersonaMetadata(BaseModel):
    id: str
    name: str
    persona_type: str
    age: int
    gender: str
    occupation: str
    district: str
    risk_tier: str
    risk_score: float
    trajectory_trend: str
    clinical_summary: str
    key_vitals: Dict[str, Any]
    key_labs: Dict[str, Any]


SYNTHETIC_PERSONAS: Dict[str, PersonaMetadata] = {}


KNOWN_PERSONA_USERS = {
    "citizen-ramesh-patel-01": ("citizen-user-01", "91-4829-1029-4820"),
    "citizen-lakshmi-devi-02": ("citizen-lakshmi-id", "91-3829-9402-1029"),
    "citizen-vikram-singh-03": ("citizen-vikram-id", "91-5829-3019-9402"),
    "citizen-priya-sharma-04": ("citizen-priya-id", "91-1029-4820-3829"),
}


def _create_user_and_citizen(
    cid: str,
    email: str,
    first_name: str,
    last_name: str,
    birth_date: str,
    gender: Gender,
    phone: str,
    district: str,
    ward: str,
    tenant_id: str = "karnataka_state_health",
) -> CitizenRecord:
    existing_citizen = store.get_citizen(cid)
    if existing_citizen:
        uid = existing_citizen.user_id
        abha_id = existing_citizen.abha_id
    elif cid in KNOWN_PERSONA_USERS:
        uid, abha_id = KNOWN_PERSONA_USERS[cid]
    else:
        uid = f"user-{cid}"
        abha_id = f"91-{abs(hash(cid)) % 9000 + 1000}-{abs(hash(email)) % 9000 + 1000}-2026"

    store.add_user(
        UserRecord(
            id=uid,
            tenant_id=tenant_id,
            email=email,
            hashed_password=get_password_hash("password123"),
            role=UserRole.CITIZEN,
            full_name=f"{first_name} {last_name}",
            assigned_jurisdiction=ward,
            assigned_patients=[],
        )
    )

    citizen = CitizenRecord(
        id=cid,
        tenant_id=tenant_id,
        user_id=uid,
        abha_id=abha_id,
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        gender=gender,
        phone=phone,
        state="Karnataka",
        district=district,
        sub_district=f"{district} Taluk",
        village_or_ward=ward,
    )
    store.add_citizen(citizen)
    return citizen


def _add_obs(cid: str, code: str, val: float, unit: str, loinc: str, name: str, tenant_id: str = "karnataka_state_health"):
    store.add_observation(
        Observation(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            citizen_id=cid,
            code=code,
            value=val,
            unit=unit,
            loinc_code=loinc,
            display_name=name,
            source="SCREENING_SESSION",
        )
    )


def seed_all_synthetic_personas():
    """Seeds all 12 personas and their comprehensive clinical artifacts into the platform store."""
    now = datetime.now(timezone.utc)

    # =========================================================================
    # 1. Healthy / Low Risk: Priya Sharma
    # =========================================================================
    c1_id = "citizen-priya-sharma-04"
    c1 = _create_user_and_citizen(
        cid=c1_id,
        email="priya@sevahealth.ai",
        first_name="Priya",
        last_name="Sharma",
        birth_date="1998-02-14",
        gender=Gender.FEMALE,
        phone="+91 94480 99887",
        district="Mysuru",
        ward="Gokulam Ward 3",
    )
    _add_obs(c1_id, "SYSTOLIC_BP", 112.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c1_id, "DIASTOLIC_BP", 72.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c1_id, "FASTING_GLUCOSE", 86.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c1_id, "HBA1C", 5.0, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c1_id, "BMI", 20.8, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c1_id, "WAIST_CIRCUMFERENCE", 73.0, "cm", "8280-0", "Waist Circumference")
    _add_obs(c1_id, "TOTAL_CHOLESTEROL", 165.0, "mg/dL", "2093-3", "Total Cholesterol")
    _add_obs(c1_id, "TRIGLYCERIDES", 95.0, "mg/dL", "2571-8", "Triglycerides")
    _add_obs(c1_id, "EGFR", 115.0, "mL/min/1.73m2", "33914-3", "eGFR")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-priya-04",
            tenant_id=c1.tenant_id,
            citizen_id=c1_id,
            overall_score=0.12,
            overall_tier=RiskTier.LOW,
            domains=DomainRiskScores(
                diabetes_risk=0.08,
                hypertension_risk=0.09,
                cardiovascular_risk=0.06,
                metabolic_syndrome_risk=0.10,
                ckd_risk=0.04,
                fatty_liver_risk=0.05,
            ),
            trajectory=TrajectoryTrend.IMPROVING,
            confidence_score=0.96,
            top_drivers=[
                RiskDriver(
                    feature_name="Optimal Glycemia",
                    observed_value="HbA1c 5.0%",
                    target_value="< 5.7%",
                    impact_weight=0.05,
                    category="BIOMETRIC",
                )
            ],
            protective_factors=[
                ProtectiveFactor(feature_name="High Physical Activity", observed_value="10,500 steps/day", impact_weight=-0.25),
                ProtectiveFactor(feature_name="Optimal Body Composition", observed_value="BMI 20.8", impact_weight=-0.20),
            ],
            clinical_summary="Optimal metabolic and cardiovascular profile. Sustain routine preventive lifestyle.",
        )
    )

    store.set_care_plan(
        CarePlan(
            id="careplan-priya-04",
            tenant_id=c1.tenant_id,
            citizen_id=c1_id,
            risk_assessment_id="risk-priya-04",
            title="SevaHealth Active Wellness & Cardiorespiratory Maintenance",
            focus_domain="Optimal Metabolic Health & Longevity",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            adherence_percentage=94.0,
            nutrition_guidance="Balanced whole foods, high fiber, lean proteins, and hydration.",
            activity_guidance="Sustain 10,000+ daily steps with 3 weekly aerobic cross-training sessions.",
            sleep_guidance="8 hours restful nightly sleep.",
            stress_guidance="Mindful meditation and breathwork.",
            daily_tasks=[
                DailyTask(
                    id=f"priya-task-{d}",
                    day=d,
                    pillar=InterventionPillar.PHYSICAL_ACTIVITY if d % 2 == 0 else InterventionPillar.NUTRITION,
                    title=f"Day {d}: 10,000 Steps Daily Target" if d % 2 == 0 else f"Day {d}: Plant-rich anti-inflammatory meal",
                    description="Cardiovascular conditioning maintenance.",
                    target_metric="10,000 steps" if d % 2 == 0 else "1 whole grain meal",
                    completed=True,
                )
                for d in range(1, 31)
            ],
            clinician_reviewed=True,
            clinician_id="doctor-user-01",
        )
    )

    store.wearable_data[c1_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c1_id, days=14, base_rhr=58.0, base_hrv=68.0, base_steps=10500, stress_trend=False
    )

    store.set_trajectory_snapshots(
        c1_id,
        [
            RiskSnapshot(
                citizen_id=c1_id,
                timestamp=now - timedelta(days=180),
                domain_scores={"metabolic": 0.14, "diabetes": 0.10, "hypertension": 0.12, "cardiovascular": 0.08, "obesity": 0.12, "renal": 0.05, "lifestyle": 0.08},
                domain_tiers={"metabolic": "LOW", "diabetes": "LOW", "hypertension": "LOW", "cardiovascular": "LOW", "obesity": "LOW", "renal": "LOW", "lifestyle": "LOW"},
                key_biomarkers={"HBA1C": 5.1, "SYSTOLIC_BP": 114.0, "BMI": 21.0, "STEPS": 9800},
            ),
            RiskSnapshot(
                citizen_id=c1_id,
                timestamp=now,
                domain_scores={"metabolic": 0.12, "diabetes": 0.08, "hypertension": 0.09, "cardiovascular": 0.06, "obesity": 0.10, "renal": 0.04, "lifestyle": 0.06},
                domain_tiers={"metabolic": "LOW", "diabetes": "LOW", "hypertension": "LOW", "cardiovascular": "LOW", "obesity": "LOW", "renal": "LOW", "lifestyle": "LOW"},
                key_biomarkers={"HBA1C": 5.0, "SYSTOLIC_BP": 112.0, "BMI": 20.8, "STEPS": 10500},
            ),
        ],
    )

    SYNTHETIC_PERSONAS[c1_id] = PersonaMetadata(
        id=c1_id,
        name="Priya Sharma",
        persona_type="Healthy / Low Risk",
        age=26,
        gender="FEMALE",
        occupation="Fitness Coach & Marathoner",
        district="Mysuru",
        risk_tier="LOW",
        risk_score=0.12,
        trajectory_trend="IMPROVING",
        clinical_summary="Excellent physiological and cardiorespiratory fitness across all NCD markers.",
        key_vitals={"bp": "112/72 mmHg", "bmi": 20.8, "steps": 10500},
        key_labs={"hba1c": "5.0%", "fbg": "86 mg/dL", "cholesterol": "165 mg/dL"},
    )

    # =========================================================================
    # 2. Prediabetes: Ramesh Patel
    # =========================================================================
    c2_id = "citizen-ramesh-patel-01"
    c2 = _create_user_and_citizen(
        cid=c2_id,
        email="citizen@sevahealth.ai",
        first_name="Ramesh",
        last_name="Patel",
        birth_date="1978-04-12",
        gender=Gender.MALE,
        phone="+91 98450 12345",
        district="Bengaluru Rural",
        ward="Ward 12",
    )
    _add_obs(c2_id, "SYSTOLIC_BP", 138.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c2_id, "DIASTOLIC_BP", 88.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c2_id, "FASTING_GLUCOSE", 118.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c2_id, "HBA1C", 6.2, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c2_id, "BMI", 27.2, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c2_id, "WAIST_CIRCUMFERENCE", 96.0, "cm", "8280-0", "Waist Circumference")
    _add_obs(c2_id, "TRIGLYCERIDES", 185.0, "mg/dL", "2571-8", "Triglycerides")
    _add_obs(c2_id, "HDL_CHOLESTEROL", 38.0, "mg/dL", "2085-9", "HDL Cholesterol")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-ramesh-01",
            tenant_id=c2.tenant_id,
            citizen_id=c2_id,
            overall_score=0.68,
            overall_tier=RiskTier.HIGH,
            domains=DomainRiskScores(
                diabetes_risk=0.74,
                hypertension_risk=0.62,
                cardiovascular_risk=0.45,
                metabolic_syndrome_risk=0.70,
                ckd_risk=0.25,
                fatty_liver_risk=0.55,
            ),
            trajectory=TrajectoryTrend.DETERIORATING,
            confidence_score=0.94,
            top_drivers=[
                RiskDriver(feature_name="Prediabetic Impaired Glycemia", observed_value="HbA1c 6.2%, FBG 118", target_value="< 5.7%", impact_weight=0.26),
                RiskDriver(feature_name="Prehypertension Vascular Strain", observed_value="138/88 mmHg", target_value="< 120/80", impact_weight=0.19),
                RiskDriver(feature_name="Central Visceral Adiposity", observed_value="Waist 96 cm, BMI 27.2", target_value="Waist < 90", impact_weight=0.15),
            ],
            clinical_summary="High prediabetes and metabolic progression risk. Clinical review recommended.",
        )
    )

    # 30-Day Care Plan
    tasks_c2 = [
        DailyTask(
            id=f"ramesh-task-{d}",
            day=d,
            pillar=InterventionPillar.PHYSICAL_ACTIVITY if d % 2 == 0 else InterventionPillar.NUTRITION,
            title=f"Day {d}: 20-Minute Post-Dinner Brisk Walk" if d % 2 == 0 else f"Day {d}: Swap White Rice for Foxtail Millet",
            description="Blunts post-prandial glycemic excursions." if d % 2 == 0 else "High-fiber whole grain stabilizes insulin.",
            target_metric="2,500 steps" if d % 2 == 0 else "1 millet serving",
            completed=(d <= 6),
        )
        for d in range(1, 31)
    ]
    store.set_care_plan(
        CarePlan(
            id="careplan-ramesh-01",
            tenant_id=c2.tenant_id,
            citizen_id=c2_id,
            risk_assessment_id="risk-ramesh-01",
            title="SevaHealth 30-Day Glycemic Stabilization Journey",
            focus_domain="Prediabetes Reversal & Vascular Protection",
            start_date=date.today(),
            end_date=date.today(),
            adherence_percentage=20.0,
            nutrition_guidance="Replace 50% of refined grains with ragi and foxtail millet.",
            activity_guidance="Target 150 minutes of moderate aerobic activity weekly.",
            sleep_guidance="Consistent 7.5 hours nightly sleep with screen cutoff.",
            stress_guidance="Daily 5-minute diaphragmatic breathing.",
            daily_tasks=tasks_c2,
        )
    )

    store.wearable_data[c2_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c2_id, days=14, base_rhr=76.0, base_hrv=36.0, base_steps=5200, stress_trend=True
    )

    store.add_alert({
        "id": "alert-ramesh-01",
        "citizen_id": c2_id,
        "urgency": "PRIORITY",
        "alert_type": "PREDIABETES_GLYCEMIC_SPIKE",
        "message": "Impaired fasting glucose (118 mg/dL) and HbA1c (6.2%) indicative of prediabetes.",
        "created_at": "2026-09-15T10:30:00Z",
        "is_acknowledged": False,
    })

    store.set_trajectory_snapshots(
        c2_id,
        [
            RiskSnapshot(
                citizen_id=c2_id,
                timestamp=now - timedelta(days=180),
                domain_scores={"metabolic": 0.35, "diabetes": 0.38, "hypertension": 0.30, "cardiovascular": 0.28, "obesity": 0.36, "renal": 0.12, "lifestyle": 0.28},
                domain_tiers={"metabolic": "MODERATE", "diabetes": "MODERATE", "hypertension": "MODERATE", "cardiovascular": "MODERATE", "obesity": "MODERATE", "renal": "LOW", "lifestyle": "LOW"},
                key_biomarkers={"HBA1C": 5.7, "FASTING_GLUCOSE": 102.0, "SYSTOLIC_BP": 126.0, "BMI": 25.5, "STEPS": 8200},
            ),
            RiskSnapshot(
                citizen_id=c2_id,
                timestamp=now - timedelta(days=90),
                domain_scores={"metabolic": 0.50, "diabetes": 0.52, "hypertension": 0.46, "cardiovascular": 0.36, "obesity": 0.52, "renal": 0.16, "lifestyle": 0.44},
                domain_tiers={"metabolic": "MODERATE", "diabetes": "MODERATE", "hypertension": "MODERATE", "cardiovascular": "MODERATE", "obesity": "MODERATE", "renal": "LOW", "lifestyle": "MODERATE"},
                key_biomarkers={"HBA1C": 6.0, "FASTING_GLUCOSE": 110.0, "SYSTOLIC_BP": 132.0, "BMI": 26.4, "STEPS": 6400},
            ),
            RiskSnapshot(
                citizen_id=c2_id,
                timestamp=now,
                domain_scores={"metabolic": 0.65, "diabetes": 0.68, "hypertension": 0.62, "cardiovascular": 0.44, "obesity": 0.64, "renal": 0.22, "lifestyle": 0.58},
                domain_tiers={"metabolic": "HIGH", "diabetes": "HIGH", "hypertension": "HIGH", "cardiovascular": "MODERATE", "obesity": "HIGH", "renal": "MODERATE", "lifestyle": "HIGH"},
                key_biomarkers={"HBA1C": 6.2, "FASTING_GLUCOSE": 118.0, "SYSTOLIC_BP": 138.0, "BMI": 27.2, "STEPS": 5200},
            ),
        ],
    )

    SYNTHETIC_PERSONAS[c2_id] = PersonaMetadata(
        id=c2_id,
        name="Ramesh Patel",
        persona_type="Prediabetes",
        age=48,
        gender="MALE",
        occupation="Bank Operations Officer",
        district="Bengaluru Rural",
        risk_tier="HIGH",
        risk_score=0.68,
        trajectory_trend="DETERIORATING",
        clinical_summary="Impaired fasting glucose and prediabetes range HbA1c with worsening metabolic trajectory.",
        key_vitals={"bp": "138/88 mmHg", "bmi": 27.2, "steps": 5200},
        key_labs={"hba1c": "6.2%", "fbg": "118 mg/dL", "triglycerides": "185 mg/dL"},
    )

    # =========================================================================
    # 3. Newly Detected Hypertension Risk: Suresh Kumar
    # =========================================================================
    c3_id = "citizen-suresh-kumar-03"
    c3 = _create_user_and_citizen(
        cid=c3_id,
        email="suresh@sevahealth.ai",
        first_name="Suresh",
        last_name="Kumar",
        birth_date="1982-06-18",
        gender=Gender.MALE,
        phone="+91 97422 11223",
        district="Tumakuru",
        ward="Kora Hobli Ward 2",
    )
    _add_obs(c3_id, "SYSTOLIC_BP", 148.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c3_id, "DIASTOLIC_BP", 92.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c3_id, "FASTING_GLUCOSE", 92.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c3_id, "HBA1C", 5.3, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c3_id, "BMI", 24.6, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c3_id, "WAIST_CIRCUMFERENCE", 88.0, "cm", "8280-0", "Waist Circumference")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-suresh-03",
            tenant_id=c3.tenant_id,
            citizen_id=c3_id,
            overall_score=0.58,
            overall_tier=RiskTier.MODERATE,
            domains=DomainRiskScores(
                diabetes_risk=0.18,
                hypertension_risk=0.82,
                cardiovascular_risk=0.48,
                metabolic_syndrome_risk=0.35,
                ckd_risk=0.22,
                fatty_liver_risk=0.18,
            ),
            trajectory=TrajectoryTrend.DETERIORATING,
            confidence_score=0.92,
            top_drivers=[
                RiskDriver(feature_name="Stage 1-2 Hypertension", observed_value="148/92 mmHg", target_value="< 120/80", impact_weight=0.32),
                RiskDriver(feature_name="Elevated Dietary Sodium", observed_value="High Pickles/Papad", target_value="< 2g Sodium", impact_weight=0.18),
            ],
            clinical_summary="Asymptomatic newly detected hypertension. Recommended home BP logging and salt restriction.",
        )
    )

    store.wearable_data[c3_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c3_id, days=14, base_rhr=74.0, base_hrv=42.0, base_steps=6100, stress_trend=False
    )

    store.add_alert({
        "id": "alert-suresh-01",
        "citizen_id": c3_id,
        "urgency": "PRIORITY",
        "alert_type": "NEW_HYPERTENSION_DETECTED",
        "message": "Screening detected Stage 1-2 elevated blood pressure (148/92 mmHg). Confirmatory reading needed.",
        "created_at": now.isoformat(),
        "is_acknowledged": False,
    })

    store.add_referral(c3_id, {
        "id": "ref-suresh-01",
        "citizen_id": c3_id,
        "to_specialty": "PHC Medical Officer",
        "reason": "Ambulatory blood pressure confirmation and DASH diet prescription",
        "priority": "HIGH",
        "status": "SCHEDULED",
    })

    store.set_trajectory_snapshots(
        c3_id,
        [
            RiskSnapshot(
                citizen_id=c3_id,
                timestamp=now - timedelta(days=90),
                domain_scores={"metabolic": 0.20, "diabetes": 0.15, "hypertension": 0.40, "cardiovascular": 0.25, "obesity": 0.20, "renal": 0.15, "lifestyle": 0.25},
                domain_tiers={"metabolic": "LOW", "diabetes": "LOW", "hypertension": "MODERATE", "cardiovascular": "LOW", "obesity": "LOW", "renal": "LOW", "lifestyle": "LOW"},
                key_biomarkers={"SYSTOLIC_BP": 128.0, "DIASTOLIC_BP": 82.0, "BMI": 24.2},
            ),
            RiskSnapshot(
                citizen_id=c3_id,
                timestamp=now,
                domain_scores={"metabolic": 0.25, "diabetes": 0.18, "hypertension": 0.82, "cardiovascular": 0.48, "obesity": 0.25, "renal": 0.22, "lifestyle": 0.38},
                domain_tiers={"metabolic": "LOW", "diabetes": "LOW", "hypertension": "HIGH", "cardiovascular": "MODERATE", "obesity": "LOW", "renal": "LOW", "lifestyle": "MODERATE"},
                key_biomarkers={"SYSTOLIC_BP": 148.0, "DIASTOLIC_BP": 92.0, "BMI": 24.6},
            ),
        ],
    )

    SYNTHETIC_PERSONAS[c3_id] = PersonaMetadata(
        id=c3_id,
        name="Suresh Kumar",
        persona_type="Newly detected hypertension risk",
        age=44,
        gender="MALE",
        occupation="Primary School Teacher",
        district="Tumakuru",
        risk_tier="MODERATE",
        risk_score=0.58,
        trajectory_trend="DETERIORATING",
        clinical_summary="Newly discovered asymptomatic Stage 1-2 hypertension during community outreach camp.",
        key_vitals={"bp": "148/92 mmHg", "bmi": 24.6, "steps": 6100},
        key_labs={"hba1c": "5.3%", "fbg": "92 mg/dL", "creatinine": "0.9 mg/dL"},
    )

    # =========================================================================
    # 4. Obesity / Metabolic Risk: Anita Desai
    # =========================================================================
    c4_id = "citizen-anita-desai-04"
    c4 = _create_user_and_citizen(
        cid=c4_id,
        email="anita@sevahealth.ai",
        first_name="Anita",
        last_name="Desai",
        birth_date="1990-11-23",
        gender=Gender.FEMALE,
        phone="+91 96321 44556",
        district="Belagavi",
        ward="Tilakwadi Ward 4",
    )
    _add_obs(c4_id, "SYSTOLIC_BP", 132.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c4_id, "DIASTOLIC_BP", 84.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c4_id, "FASTING_GLUCOSE", 106.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c4_id, "HBA1C", 5.8, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c4_id, "BMI", 32.4, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c4_id, "WAIST_CIRCUMFERENCE", 98.0, "cm", "8280-0", "Waist Circumference")
    _add_obs(c4_id, "TRIGLYCERIDES", 228.0, "mg/dL", "2571-8", "Triglycerides")
    _add_obs(c4_id, "HDL_CHOLESTEROL", 36.0, "mg/dL", "2085-9", "HDL Cholesterol")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-anita-04",
            tenant_id=c4.tenant_id,
            citizen_id=c4_id,
            overall_score=0.74,
            overall_tier=RiskTier.HIGH,
            domains=DomainRiskScores(
                diabetes_risk=0.55,
                hypertension_risk=0.48,
                cardiovascular_risk=0.42,
                metabolic_syndrome_risk=0.84,
                ckd_risk=0.18,
                fatty_liver_risk=0.72,
            ),
            trajectory=TrajectoryTrend.DETERIORATING,
            confidence_score=0.91,
            top_drivers=[
                RiskDriver(feature_name="Class I Obesity", observed_value="BMI 32.4 kg/m2", target_value="BMI < 23", impact_weight=0.30),
                RiskDriver(feature_name="Atherogenic Dyslipidemia", observed_value="TG 228, HDL 36", target_value="TG < 150", impact_weight=0.24),
                RiskDriver(feature_name="Abdominal Visceral Adiposity", observed_value="Waist 98 cm", target_value="Waist < 80", impact_weight=0.20),
            ],
            clinical_summary="Metabolic syndrome cluster with fatty liver risk. Multi-pillar weight reduction required.",
        )
    )

    store.wearable_data[c4_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c4_id, days=14, base_rhr=80.0, base_hrv=32.0, base_steps=3800, stress_trend=True
    )

    store.add_alert({
        "id": "alert-anita-01",
        "citizen_id": c4_id,
        "urgency": "PRIORITY",
        "alert_type": "METABOLIC_SYNDROME_CLUSTER",
        "message": "Cluster of visceral adiposity (Waist 98cm), hypertriglyceridemia (228 mg/dL), and borderline glucose.",
        "created_at": now.isoformat(),
        "is_acknowledged": False,
    })

    store.set_trajectory_snapshots(
        c4_id,
        [
            RiskSnapshot(
                citizen_id=c4_id,
                timestamp=now - timedelta(days=120),
                domain_scores={"metabolic": 0.65, "diabetes": 0.45, "hypertension": 0.40, "cardiovascular": 0.35, "obesity": 0.70, "renal": 0.15, "lifestyle": 0.50},
                domain_tiers={"metabolic": "HIGH", "diabetes": "MODERATE", "hypertension": "MODERATE", "cardiovascular": "LOW", "obesity": "HIGH", "renal": "LOW", "lifestyle": "MODERATE"},
                key_biomarkers={"BMI": 30.2, "WAIST_CIRCUMFERENCE": 93.0, "TRIGLYCERIDES": 190.0},
            ),
            RiskSnapshot(
                citizen_id=c4_id,
                timestamp=now,
                domain_scores={"metabolic": 0.84, "diabetes": 0.55, "hypertension": 0.48, "cardiovascular": 0.42, "obesity": 0.85, "renal": 0.18, "lifestyle": 0.65},
                domain_tiers={"metabolic": "HIGH", "diabetes": "MODERATE", "hypertension": "MODERATE", "cardiovascular": "MODERATE", "obesity": "CRITICAL", "renal": "LOW", "lifestyle": "HIGH"},
                key_biomarkers={"BMI": 32.4, "WAIST_CIRCUMFERENCE": 98.0, "TRIGLYCERIDES": 228.0},
            ),
        ],
    )

    SYNTHETIC_PERSONAS[c4_id] = PersonaMetadata(
        id=c4_id,
        name="Anita Desai",
        persona_type="Obesity/metabolic risk",
        age=36,
        gender="FEMALE",
        occupation="Homemaker",
        district="Belagavi",
        risk_tier="HIGH",
        risk_score=0.74,
        trajectory_trend="DETERIORATING",
        clinical_summary="Metabolic syndrome phenotype with Class I obesity and non-alcoholic fatty liver risk.",
        key_vitals={"bp": "132/84 mmHg", "bmi": 32.4, "steps": 3800},
        key_labs={"hba1c": "5.8%", "fbg": "106 mg/dL", "triglycerides": "228 mg/dL"},
    )

    # =========================================================================
    # 5. High Cardiovascular Risk: Vikram Singh
    # =========================================================================
    c5_id = "citizen-vikram-singh-03"
    c5 = _create_user_and_citizen(
        cid=c5_id,
        email="vikram@sevahealth.ai",
        first_name="Vikram",
        last_name="Singh",
        birth_date="1974-11-05",
        gender=Gender.MALE,
        phone="+91 99887 76655",
        district="Hassan",
        ward="Highway Corridor Ward",
    )
    _add_obs(c5_id, "SYSTOLIC_BP", 154.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c5_id, "DIASTOLIC_BP", 94.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c5_id, "FASTING_GLUCOSE", 112.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c5_id, "HBA1C", 5.9, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c5_id, "BMI", 28.2, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c5_id, "TOTAL_CHOLESTEROL", 248.0, "mg/dL", "2093-3", "Total Cholesterol")
    _add_obs(c5_id, "TRIGLYCERIDES", 250.0, "mg/dL", "2571-8", "Triglycerides")
    _add_obs(c5_id, "HDL_CHOLESTEROL", 34.0, "mg/dL", "2085-9", "HDL Cholesterol")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-vikram-05",
            tenant_id=c5.tenant_id,
            citizen_id=c5_id,
            overall_score=0.82,
            overall_tier=RiskTier.CRITICAL,
            domains=DomainRiskScores(
                diabetes_risk=0.45,
                hypertension_risk=0.86,
                cardiovascular_risk=0.88,
                metabolic_syndrome_risk=0.72,
                ckd_risk=0.32,
                fatty_liver_risk=0.50,
            ),
            trajectory=TrajectoryTrend.DETERIORATING,
            confidence_score=0.95,
            top_drivers=[
                RiskDriver(feature_name="10-Year WHO-SEAR CVD Risk > 20%", observed_value="High Risk Matrix", target_value="< 10%", impact_weight=0.35),
                RiskDriver(feature_name="Active Tobacco Smoking", observed_value="15 Bidis/day", target_value="0 (Cessation)", impact_weight=0.28),
                RiskDriver(feature_name="Severe Hypercholesterolemia", observed_value="Total Chol 248 mg/dL", target_value="< 200", impact_weight=0.22),
            ],
            clinical_summary="High cardiovascular atherosclerotic disease risk. Urgent statin and smoking cessation needed.",
        )
    )

    store.wearable_data[c5_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c5_id, days=14, base_rhr=82.0, base_hrv=26.0, base_steps=4100, stress_trend=True
    )

    store.add_alert({
        "id": "alert-vikram-01",
        "citizen_id": c5_id,
        "urgency": "EMERGENCY",
        "alert_type": "HIGH_CARDIOVASCULAR_ISCHEMIC_RISK",
        "message": "WHO-SEAR 10-year CVD risk exceeds 20% in active smoker with BP 154/94 and Chol 248 mg/dL.",
        "created_at": now.isoformat(),
        "is_acknowledged": False,
    })

    store.add_referral(c5_id, {
        "id": "ref-vikram-01",
        "citizen_id": c5_id,
        "to_specialty": "Cardiology Consultation & Tobacco Cessation",
        "reason": "Elevated 10-year CVD event probability requiring medical officer statin evaluation",
        "priority": "HIGH",
        "status": "PENDING",
    })

    SYNTHETIC_PERSONAS[c5_id] = PersonaMetadata(
        id=c5_id,
        name="Vikram Singh",
        persona_type="High cardiovascular risk",
        age=52,
        gender="MALE",
        occupation="Heavy Transport Driver",
        district="Hassan",
        risk_tier="CRITICAL",
        risk_score=0.82,
        trajectory_trend="DETERIORATING",
        clinical_summary="Heavy smoker with stage 2 hypertension, dyslipidemia, and elevated 10-year CVD mortality matrix.",
        key_vitals={"bp": "154/94 mmHg", "bmi": 28.2, "steps": 4100},
        key_labs={"hba1c": "5.9%", "cholesterol": "248 mg/dL", "triglycerides": "250 mg/dL"},
    )

    # =========================================================================
    # 6. Improving Citizen: Meera Bai
    # =========================================================================
    c6_id = "citizen-meera-bai-06"
    c6 = _create_user_and_citizen(
        cid=c6_id,
        email="meera@sevahealth.ai",
        first_name="Meera",
        last_name="Bai",
        birth_date="1980-03-15",
        gender=Gender.FEMALE,
        phone="+91 94801 33445",
        district="Dharwad",
        ward="Hubballi East Ward 7",
    )
    _add_obs(c6_id, "SYSTOLIC_BP", 120.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c6_id, "DIASTOLIC_BP", 78.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c6_id, "FASTING_GLUCOSE", 94.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c6_id, "HBA1C", 5.6, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c6_id, "BMI", 24.9, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c6_id, "WAIST_CIRCUMFERENCE", 84.0, "cm", "8280-0", "Waist Circumference")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-meera-06",
            tenant_id=c6.tenant_id,
            citizen_id=c6_id,
            overall_score=0.22,
            overall_tier=RiskTier.LOW,
            domains=DomainRiskScores(
                diabetes_risk=0.18,
                hypertension_risk=0.15,
                cardiovascular_risk=0.12,
                metabolic_syndrome_risk=0.20,
                ckd_risk=0.08,
                fatty_liver_risk=0.14,
            ),
            trajectory=TrajectoryTrend.IMPROVING,
            confidence_score=0.96,
            top_drivers=[],
            protective_factors=[
                ProtectiveFactor(feature_name="Glycemic Reversal Success", observed_value="HbA1c dropped 6.4% -> 5.6%", impact_weight=-0.35),
                ProtectiveFactor(feature_name="Active Adherence to Millet Diet", observed_value="88% Task Completion", impact_weight=-0.28),
            ],
            clinical_summary="Prediabetes reversal confirmed. Biomarkers normalized into healthy reference ranges.",
        )
    )

    store.set_care_plan(
        CarePlan(
            id="careplan-meera-06",
            tenant_id=c6.tenant_id,
            citizen_id=c6_id,
            risk_assessment_id="risk-meera-06",
            title="SevaHealth 60-Day Glycemic Stabilization & Reversal Journey",
            focus_domain="Prediabetes Reversal & Vascular Protection",
            start_date=date.today() - timedelta(days=60),
            end_date=date.today(),
            adherence_percentage=88.0,
            nutrition_guidance="Replaced white rice with foxtail millet and ragi; blunted post-meal spikes.",
            activity_guidance="Completed 7,500 daily steps with post-meal walking regimen.",
            sleep_guidance="7.5 hours nightly sleep.",
            stress_guidance="5-minute daily breathing.",
            daily_tasks=[
                DailyTask(
                    id=f"meera-task-{d}",
                    day=d,
                    pillar=InterventionPillar.PHYSICAL_ACTIVITY if d % 2 == 0 else InterventionPillar.NUTRITION,
                    title=f"Day {d}: 25-minute brisk walk" if d % 2 == 0 else f"Day {d}: Millet diet adherence",
                    description="Glycemic excursion blunting.",
                    completed=(d <= 26),
                )
                for d in range(1, 31)
            ],
            clinician_reviewed=True,
            clinician_id="doctor-user-01",
        )
    )

    store.wearable_data[c6_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c6_id, days=14, base_rhr=64.0, base_hrv=54.0, base_steps=8400, stress_trend=False
    )

    store.set_trajectory_snapshots(
        c6_id,
        [
            RiskSnapshot(
                citizen_id=c6_id,
                timestamp=now - timedelta(days=90),
                domain_scores={"metabolic": 0.68, "diabetes": 0.72, "hypertension": 0.60, "cardiovascular": 0.45, "obesity": 0.65, "renal": 0.15, "lifestyle": 0.55},
                domain_tiers={"metabolic": "HIGH", "diabetes": "HIGH", "hypertension": "HIGH", "cardiovascular": "MODERATE", "obesity": "HIGH", "renal": "LOW", "lifestyle": "HIGH"},
                key_biomarkers={"HBA1C": 6.4, "FASTING_GLUCOSE": 122.0, "SYSTOLIC_BP": 138.0, "BMI": 28.1, "STEPS": 4500},
            ),
            RiskSnapshot(
                citizen_id=c6_id,
                timestamp=now,
                domain_scores={"metabolic": 0.20, "diabetes": 0.18, "hypertension": 0.15, "cardiovascular": 0.12, "obesity": 0.22, "renal": 0.08, "lifestyle": 0.14},
                domain_tiers={"metabolic": "LOW", "diabetes": "LOW", "hypertension": "LOW", "cardiovascular": "LOW", "obesity": "LOW", "renal": "LOW", "lifestyle": "LOW"},
                key_biomarkers={"HBA1C": 5.6, "FASTING_GLUCOSE": 94.0, "SYSTOLIC_BP": 120.0, "BMI": 24.9, "STEPS": 8400},
            ),
        ],
    )

    SYNTHETIC_PERSONAS[c6_id] = PersonaMetadata(
        id=c6_id,
        name="Meera Bai",
        persona_type="Improving citizen",
        age=46,
        gender="FEMALE",
        occupation="Master Tailor",
        district="Dharwad",
        risk_tier="LOW",
        risk_score=0.22,
        trajectory_trend="IMPROVING",
        clinical_summary="Successful 60-day prediabetes reversal with normalized blood pressure, BMI, and HbA1c.",
        key_vitals={"bp": "120/78 mmHg", "bmi": 24.9, "steps": 8400},
        key_labs={"hba1c": "5.6%", "fbg": "94 mg/dL", "cholesterol": "172 mg/dL"},
    )

    # =========================================================================
    # 7. Deteriorating Citizen: Rajesh Verma
    # =========================================================================
    c7_id = "citizen-rajesh-verma-07"
    c7 = _create_user_and_citizen(
        cid=c7_id,
        email="rajesh@sevahealth.ai",
        first_name="Rajesh",
        last_name="Verma",
        birth_date="1976-08-30",
        gender=Gender.MALE,
        phone="+91 97312 88776",
        district="Bengaluru Urban",
        ward="Koramangala Ward 68",
    )
    _add_obs(c7_id, "SYSTOLIC_BP", 144.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c7_id, "DIASTOLIC_BP", 92.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c7_id, "FASTING_GLUCOSE", 121.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c7_id, "HBA1C", 6.3, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c7_id, "BMI", 28.5, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c7_id, "WAIST_CIRCUMFERENCE", 96.0, "cm", "8280-0", "Waist Circumference")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-rajesh-07",
            tenant_id=c7.tenant_id,
            citizen_id=c7_id,
            overall_score=0.70,
            overall_tier=RiskTier.HIGH,
            domains=DomainRiskScores(
                diabetes_risk=0.76,
                hypertension_risk=0.72,
                cardiovascular_risk=0.58,
                metabolic_syndrome_risk=0.74,
                ckd_risk=0.28,
                fatty_liver_risk=0.62,
            ),
            trajectory=TrajectoryTrend.DETERIORATING,
            confidence_score=0.94,
            top_drivers=[
                RiskDriver(feature_name="Rapid Trajectory Velocity", observed_value="+38% Risk Escalation", target_value="Stable", impact_weight=0.34),
                RiskDriver(feature_name="Physical Activity Collapse", observed_value="Steps 2,900/day (-62%)", target_value="> 7,000", impact_weight=0.25),
            ],
            clinical_summary="Rapidly deteriorating trajectory across metabolic and vascular dimensions.",
        )
    )

    store.wearable_data[c7_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c7_id, days=14, base_rhr=79.0, base_hrv=29.0, base_steps=2900, stress_trend=True
    )

    store.add_alert({
        "id": "alert-rajesh-01",
        "citizen_id": c7_id,
        "urgency": "PRIORITY",
        "alert_type": "RAPID_DETERIORATION_VELOCITY",
        "message": "Longitudinal risk accelerated by 38% over 90 days. Physical activity collapsed to 2,900 steps.",
        "created_at": now.isoformat(),
        "is_acknowledged": False,
    })

    store.set_trajectory_snapshots(
        c7_id,
        [
            RiskSnapshot(
                citizen_id=c7_id,
                timestamp=now - timedelta(days=180),
                domain_scores={"metabolic": 0.32, "diabetes": 0.30, "hypertension": 0.28, "cardiovascular": 0.25, "obesity": 0.30, "renal": 0.12, "lifestyle": 0.25},
                domain_tiers={"metabolic": "LOW", "diabetes": "LOW", "hypertension": "LOW", "cardiovascular": "LOW", "obesity": "LOW", "renal": "LOW", "lifestyle": "LOW"},
                key_biomarkers={"HBA1C": 5.5, "FASTING_GLUCOSE": 98.0, "SYSTOLIC_BP": 124.0, "BMI": 25.2, "STEPS": 7800},
            ),
            RiskSnapshot(
                citizen_id=c7_id,
                timestamp=now,
                domain_scores={"metabolic": 0.74, "diabetes": 0.76, "hypertension": 0.72, "cardiovascular": 0.58, "obesity": 0.72, "renal": 0.28, "lifestyle": 0.78},
                domain_tiers={"metabolic": "HIGH", "diabetes": "HIGH", "hypertension": "HIGH", "cardiovascular": "MODERATE", "obesity": "HIGH", "renal": "LOW", "lifestyle": "HIGH"},
                key_biomarkers={"HBA1C": 6.3, "FASTING_GLUCOSE": 121.0, "SYSTOLIC_BP": 144.0, "BMI": 28.5, "STEPS": 2900},
            ),
        ],
    )

    SYNTHETIC_PERSONAS[c7_id] = PersonaMetadata(
        id=c7_id,
        name="Rajesh Verma",
        persona_type="Deteriorating citizen",
        age=50,
        gender="MALE",
        occupation="Corporate Auditor",
        district="Bengaluru Urban",
        risk_tier="HIGH",
        risk_score=0.70,
        trajectory_trend="DETERIORATING",
        clinical_summary="Rapid upward trajectory drift across glucose, blood pressure, and weight following lifestyle collapse.",
        key_vitals={"bp": "144/92 mmHg", "bmi": 28.5, "steps": 2900},
        key_labs={"hba1c": "6.3%", "fbg": "121 mg/dL", "triglycerides": "210 mg/dL"},
    )

    # =========================================================================
    # 8. Elderly High-Risk Citizen: Lakshmi Devi
    # =========================================================================
    c8_id = "citizen-lakshmi-devi-02"
    c8 = _create_user_and_citizen(
        cid=c8_id,
        email="lakshmi@sevahealth.ai",
        first_name="Lakshmi",
        last_name="Devi",
        birth_date="1956-08-20",
        gender=Gender.FEMALE,
        phone="+91 97410 54321",
        district="Mandya",
        ward="Koppa Village",
    )
    _add_obs(c8_id, "SYSTOLIC_BP", 168.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c8_id, "DIASTOLIC_BP", 94.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c8_id, "FASTING_GLUCOSE", 96.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c8_id, "HBA1C", 5.5, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c8_id, "BMI", 24.2, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c8_id, "SERUM_CREATININE", 1.45, "mg/dL", "2160-0", "Serum Creatinine")
    _add_obs(c8_id, "EGFR", 46.0, "mL/min/1.73m2", "33914-3", "eGFR")

    p2_risk = RiskAssessment(
        id="risk-lakshmi-02",
        tenant_id=c8.tenant_id,
        citizen_id=c8_id,
        overall_score=0.86,
        overall_tier=RiskTier.CRITICAL,
        domains=DomainRiskScores(
            diabetes_risk=0.18,
            hypertension_risk=0.94,
            cardiovascular_risk=0.85,
            metabolic_syndrome_risk=0.42,
            ckd_risk=0.72,
            fatty_liver_risk=0.25,
        ),
        trajectory=TrajectoryTrend.DETERIORATING,
        confidence_score=0.96,
        top_drivers=[
            RiskDriver(feature_name="Isolated Systolic Hypertension", observed_value="168/94 mmHg", target_value="< 130/80", impact_weight=0.38),
            RiskDriver(feature_name="Stage 3 Chronic Kidney Disease", observed_value="eGFR 46 mL/min", target_value="> 60", impact_weight=0.30),
        ],
        clinical_summary="CRITICAL HYPERTENSIVE STRAIN & CKD: Urgent medical officer triage and renal protection required.",
    )
    store.add_risk_assessment(p2_risk)

    store.add_triage_case(
        ClinicalTriageCase(
            id="triage-lakshmi-01",
            tenant_id=c8.tenant_id,
            citizen_id=c8_id,
            citizen_name="Lakshmi Devi",
            risk_assessment_id="risk-lakshmi-02",
            urgency=TriageUrgency.EMERGENT,
            escalation_reason="Severe Stage 2 Hypertension (168/94 mmHg) and eGFR 46 mL/min in elderly citizen.",
            soap_note=SOAPReport(
                subjective="Elderly female (age 68) reports morning occipital headaches and ankle swelling.",
                objective="BP 168/94 mmHg confirmed. Serum creatinine 1.45 mg/dL, eGFR 46 mL/min.",
                assessment="Severe Stage 2 Essential Hypertension with Stage 3 Chronic Kidney Disease.",
                plan="1. Immediate Medical Officer evaluation. 2. Low sodium (< 1.5g). 3. Dose-adjusted ACEi/ARB review.",
            ),
        )
    )

    store.wearable_data[c8_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c8_id, days=14, base_rhr=78.0, base_hrv=24.0, base_steps=3100, stress_trend=True
    )

    store.add_alert({
        "id": "alert-lakshmi-01",
        "citizen_id": c8_id,
        "urgency": "EMERGENCY",
        "alert_type": "CRITICAL_HYPERTENSIVE_URGENCY",
        "message": "Systolic BP 168 mmHg and reduced renal clearance (eGFR 46) detected.",
        "created_at": now.isoformat(),
        "is_acknowledged": False,
    })

    SYNTHETIC_PERSONAS[c8_id] = PersonaMetadata(
        id=c8_id,
        name="Lakshmi Devi",
        persona_type="Elderly high-risk citizen",
        age=68,
        gender="FEMALE",
        occupation="Retired Agricultural Worker",
        district="Mandya",
        risk_tier="CRITICAL",
        risk_score=0.86,
        trajectory_trend="DETERIORATING",
        clinical_summary="Severe isolated systolic hypertension with Stage 3 CKD; active emergent triage case.",
        key_vitals={"bp": "168/94 mmHg", "bmi": 24.2, "steps": 3100},
        key_labs={"hba1c": "5.5%", "creatinine": "1.45 mg/dL", "egfr": "46 mL/min"},
    )

    # =========================================================================
    # 9. Sedentary Young Adult: Rohan Nair
    # =========================================================================
    c9_id = "citizen-rohan-nair-09"
    c9 = _create_user_and_citizen(
        cid=c9_id,
        email="rohan@sevahealth.ai",
        first_name="Rohan",
        last_name="Nair",
        birth_date="2002-05-10",
        gender=Gender.MALE,
        phone="+91 99001 22334",
        district="Bengaluru Urban",
        ward="Whitefield Tech Corridor",
    )
    _add_obs(c9_id, "SYSTOLIC_BP", 128.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c9_id, "DIASTOLIC_BP", 84.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c9_id, "FASTING_GLUCOSE", 98.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c9_id, "HBA1C", 5.4, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c9_id, "BMI", 26.5, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c9_id, "TRIGLYCERIDES", 195.0, "mg/dL", "2571-8", "Triglycerides")
    _add_obs(c9_id, "HDL_CHOLESTEROL", 38.0, "mg/dL", "2085-9", "HDL Cholesterol")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-rohan-09",
            tenant_id=c9.tenant_id,
            citizen_id=c9_id,
            overall_score=0.42,
            overall_tier=RiskTier.MODERATE,
            domains=DomainRiskScores(
                diabetes_risk=0.28,
                hypertension_risk=0.38,
                cardiovascular_risk=0.32,
                metabolic_syndrome_risk=0.48,
                ckd_risk=0.10,
                fatty_liver_risk=0.35,
            ),
            trajectory=TrajectoryTrend.DETERIORATING,
            confidence_score=0.90,
            top_drivers=[
                RiskDriver(feature_name="Severe Sedentary Physical Inactivity", observed_value="2,400 steps/day", target_value="> 8,000", impact_weight=0.32),
                RiskDriver(feature_name="Autonomic Tone Deconditioning", observed_value="Resting HR 82 bpm, HRV 28 ms", target_value="RHR < 70", impact_weight=0.22),
            ],
            clinical_summary="Early sedentary deconditioning in young tech professional. Proactive habit intervention indicated.",
        )
    )

    store.wearable_data[c9_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c9_id, days=14, base_rhr=82.0, base_hrv=28.0, base_steps=2400, stress_trend=True
    )

    SYNTHETIC_PERSONAS[c9_id] = PersonaMetadata(
        id=c9_id,
        name="Rohan Nair",
        persona_type="Sedentary young adult",
        age=24,
        gender="MALE",
        occupation="Software Engineer (Remote)",
        district="Bengaluru Urban",
        risk_tier="MODERATE",
        risk_score=0.42,
        trajectory_trend="DETERIORATING",
        clinical_summary="Deskbound young professional with under 2,500 daily steps, elevated resting HR, and early dyslipidemia.",
        key_vitals={"bp": "128/84 mmHg", "bmi": 26.5, "steps": 2400},
        key_labs={"hba1c": "5.4%", "fbg": "98 mg/dL", "triglycerides": "195 mg/dL"},
    )

    # =========================================================================
    # 10. Multiple-Risk Citizen: Gurpreet Kaur
    # =========================================================================
    c10_id = "citizen-gurpreet-kaur-10"
    c10 = _create_user_and_citizen(
        cid=c10_id,
        email="gurpreet@sevahealth.ai",
        first_name="Gurpreet",
        last_name="Kaur",
        birth_date="1968-07-12",
        gender=Gender.FEMALE,
        phone="+91 98112 55443",
        district="Bidar",
        ward="Gurudwara Colony Ward 1",
    )
    _add_obs(c10_id, "SYSTOLIC_BP", 156.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c10_id, "DIASTOLIC_BP", 96.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c10_id, "FASTING_GLUCOSE", 144.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c10_id, "HBA1C", 7.4, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c10_id, "BMI", 31.8, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c10_id, "WAIST_CIRCUMFERENCE", 102.0, "cm", "8280-0", "Waist Circumference")
    _add_obs(c10_id, "TRIGLYCERIDES", 260.0, "mg/dL", "2571-8", "Triglycerides")
    _add_obs(c10_id, "EGFR", 62.0, "mL/min/1.73m2", "33914-3", "eGFR")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-gurpreet-10",
            tenant_id=c10.tenant_id,
            citizen_id=c10_id,
            overall_score=0.88,
            overall_tier=RiskTier.CRITICAL,
            domains=DomainRiskScores(
                diabetes_risk=0.88,
                hypertension_risk=0.86,
                cardiovascular_risk=0.78,
                metabolic_syndrome_risk=0.85,
                ckd_risk=0.55,
                fatty_liver_risk=0.70,
            ),
            trajectory=TrajectoryTrend.DETERIORATING,
            confidence_score=0.97,
            top_drivers=[
                RiskDriver(feature_name="Established Type 2 Diabetes Range", observed_value="HbA1c 7.4%, FBG 144", target_value="< 5.7%", impact_weight=0.32),
                RiskDriver(feature_name="Stage 2 Uncontrolled Hypertension", observed_value="156/96 mmHg", target_value="< 130/80", impact_weight=0.28),
                RiskDriver(feature_name="Severe Central Adiposity", observed_value="Waist 102 cm, BMI 31.8", target_value="Waist < 80", impact_weight=0.20),
            ],
            clinical_summary="Multi-morbid chronic disease cluster: Diabetic glycemia, Stage 2 HTN, Obesity, and Stage 2 CKD.",
        )
    )

    store.wearable_data[c10_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c10_id, days=14, base_rhr=84.0, base_hrv=22.0, base_steps=3200, stress_trend=True
    )

    store.add_alert({
        "id": "alert-gurpreet-01",
        "citizen_id": c10_id,
        "urgency": "EMERGENCY",
        "alert_type": "MULTI_RISK_CHRONIC_CLUSTER",
        "message": "Concomitant diabetes (HbA1c 7.4%), stage 2 HTN (156/96), and obesity (BMI 31.8) detected.",
        "created_at": now.isoformat(),
        "is_acknowledged": False,
    })

    store.add_referral(c10_id, {
        "id": "ref-gurpreet-01",
        "citizen_id": c10_id,
        "to_specialty": "Multidisciplinary NCD Clinic",
        "reason": "Combined Diabetology, Cardiology, and Renal protective care coordination",
        "priority": "HIGH",
        "status": "PENDING",
    })

    SYNTHETIC_PERSONAS[c10_id] = PersonaMetadata(
        id=c10_id,
        name="Gurpreet Kaur",
        persona_type="Multiple-risk citizen",
        age=58,
        gender="FEMALE",
        occupation="Retail Business Owner",
        district="Bidar",
        risk_tier="CRITICAL",
        risk_score=0.88,
        trajectory_trend="DETERIORATING",
        clinical_summary="Complex multi-morbid profile encompassing uncontrolled diabetes, hypertension, and Class I obesity.",
        key_vitals={"bp": "156/96 mmHg", "bmi": 31.8, "steps": 3200},
        key_labs={"hba1c": "7.4%", "fbg": "144 mg/dL", "egfr": "62 mL/min"},
    )

    # =========================================================================
    # 11. DEMO HERO PERSONA: Arjun Mehta
    # =========================================================================
    c11_id = "citizen-arjun-mehta-11"
    c11 = _create_user_and_citizen(
        cid=c11_id,
        email="arjun.demo@sevahealth.ai",
        first_name="Arjun",
        last_name="Mehta",
        birth_date="1981-05-14",
        gender=Gender.MALE,
        phone="+91 98800 55667",
        district="Bengaluru Rural",
        ward="Devanahalli Town",
    )
    _add_obs(c11_id, "SYSTOLIC_BP", 126.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c11_id, "DIASTOLIC_BP", 82.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c11_id, "FASTING_GLUCOSE", 98.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c11_id, "HBA1C", 5.6, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c11_id, "BMI", 24.8, "kg/m2", "39156-5", "Body Mass Index")
    _add_obs(c11_id, "WAIST_CIRCUMFERENCE", 88.0, "cm", "8280-0", "Waist Circumference")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-arjun-base",
            tenant_id=c11.tenant_id,
            citizen_id=c11_id,
            overall_score=0.36,
            overall_tier=RiskTier.MODERATE,
            domains=DomainRiskScores(
                diabetes_risk=0.32,
                hypertension_risk=0.30,
                cardiovascular_risk=0.25,
                metabolic_syndrome_risk=0.35,
                ckd_risk=0.10,
                fatty_liver_risk=0.20,
            ),
            trajectory=TrajectoryTrend.STABLE,
            confidence_score=0.92,
            clinical_summary="Moderate baseline risk. Suitable candidate for dynamic story progression walkthrough.",
        )
    )

    store.wearable_data[c11_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c11_id, days=14, base_rhr=68.0, base_hrv=48.0, base_steps=7500, stress_trend=False
    )

    store.set_trajectory_snapshots(
        c11_id,
        [
            RiskSnapshot(
                citizen_id=c11_id,
                timestamp=now - timedelta(days=180),
                domain_scores={"metabolic": 0.32, "diabetes": 0.30, "hypertension": 0.28, "cardiovascular": 0.25, "obesity": 0.30, "renal": 0.10, "lifestyle": 0.25},
                domain_tiers={"metabolic": "MODERATE", "diabetes": "MODERATE", "hypertension": "LOW", "cardiovascular": "LOW", "obesity": "MODERATE", "renal": "LOW", "lifestyle": "LOW"},
                key_biomarkers={"HBA1C": 5.6, "FASTING_GLUCOSE": 98.0, "SYSTOLIC_BP": 126.0, "BMI": 24.8, "STEPS": 7500},
            )
        ],
    )

    SYNTHETIC_PERSONAS[c11_id] = PersonaMetadata(
        id=c11_id,
        name="Arjun Mehta",
        persona_type="Demo Hero Persona (Interactive Journey)",
        age=45,
        gender="MALE",
        occupation="Marketing Director",
        district="Bengaluru Rural",
        risk_tier="MODERATE",
        risk_score=0.36,
        trajectory_trend="STABLE",
        clinical_summary="Interactive story protagonist: Starts moderate, deteriorates silently, receives AI intervention, reverses risk.",
        key_vitals={"bp": "126/82 mmHg", "bmi": 24.8, "steps": 7500},
        key_labs={"hba1c": "5.6%", "fbg": "98 mg/dL", "cholesterol": "180 mg/dL"},
    )

    # =========================================================================
    # 12. Rural Community Field Screened Mother: Fatima Bi
    # =========================================================================
    c12_id = "citizen-fatima-bi-12"
    c12 = _create_user_and_citizen(
        cid=c12_id,
        email="fatima@sevahealth.ai",
        first_name="Fatima",
        last_name="Bi",
        birth_date="1987-09-04",
        gender=Gender.FEMALE,
        phone="+91 97400 66778",
        district="Kalaburagi",
        ward="Aland Taluk Camp",
    )
    _add_obs(c12_id, "SYSTOLIC_BP", 130.0, "mmHg", "8480-6", "Systolic Blood Pressure")
    _add_obs(c12_id, "DIASTOLIC_BP", 84.0, "mmHg", "8462-4", "Diastolic Blood Pressure")
    _add_obs(c12_id, "FASTING_GLUCOSE", 110.0, "mg/dL", "1558-6", "Fasting Blood Glucose")
    _add_obs(c12_id, "HBA1C", 5.9, "%", "4548-4", "Hemoglobin A1c")
    _add_obs(c12_id, "BMI", 26.8, "kg/m2", "39156-5", "Body Mass Index")

    store.add_risk_assessment(
        RiskAssessment(
            id="risk-fatima-12",
            tenant_id=c12.tenant_id,
            citizen_id=c12_id,
            overall_score=0.52,
            overall_tier=RiskTier.MODERATE,
            domains=DomainRiskScores(
                diabetes_risk=0.58,
                hypertension_risk=0.42,
                cardiovascular_risk=0.30,
                metabolic_syndrome_risk=0.52,
                ckd_risk=0.12,
                fatty_liver_risk=0.35,
            ),
            trajectory=TrajectoryTrend.STABLE,
            confidence_score=0.91,
            top_drivers=[
                RiskDriver(feature_name="Postpartum Prediabetes History", observed_value="HbA1c 5.9%", target_value="< 5.7%", impact_weight=0.28),
            ],
            clinical_summary="Community screening candidate with history of gestational diabetes. Enrolled in ASHA nutrition circle.",
        )
    )

    store.wearable_data[c12_id] = generate_synthetic_wearable_timeseries(
        citizen_id=c12_id, days=14, base_rhr=72.0, base_hrv=44.0, base_steps=4900, stress_trend=False
    )

    store.add_referral(c12_id, {
        "id": "ref-fatima-01",
        "citizen_id": c12_id,
        "to_specialty": "Community Nutrition Counseling",
        "reason": "Postpartum glycemic monitoring and indigenous whole-grain nutrition guidance",
        "priority": "ROUTINE",
        "status": "COMPLETED",
    })

    SYNTHETIC_PERSONAS[c12_id] = PersonaMetadata(
        id=c12_id,
        name="Fatima Bi",
        persona_type="Community Field Screened Mother",
        age=39,
        gender="FEMALE",
        occupation="Artisan Weaver",
        district="Kalaburagi",
        risk_tier="MODERATE",
        risk_score=0.52,
        trajectory_trend="STABLE",
        clinical_summary="Screened in mobile rural ASHA camp; gestational diabetes history with moderate metabolic risk.",
        key_vitals={"bp": "130/84 mmHg", "bmi": 26.8, "steps": 4900},
        key_labs={"hba1c": "5.9%", "fbg": "110 mg/dL", "cholesterol": "188 mg/dL"},
    )

    return SYNTHETIC_PERSONAS


def get_persona_summary_list() -> List[Dict[str, Any]]:
    """Returns a summarized overview list of all seeded synthetic personas."""
    if not SYNTHETIC_PERSONAS:
        seed_all_synthetic_personas()
    return [p.model_dump() for p in SYNTHETIC_PERSONAS.values()]
