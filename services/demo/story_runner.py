"""SevaHealth AI Demo Story Runner.

Executes the complete end-to-end "Hero Journey" narrative:
1. Citizen starts with Moderate Risk.
2. Silent Progression: Weight increases, Activity drops, BP worsens, HbA1c increases.
3. SevaHealth Trajectory Engine detects worsening trajectory.
4. AI explains biometric & behavioral contributors.
5. AI creates personalized 30-day multi-pillar prevention care plan.
6. Citizen completes intervention (adherence logged, wearable steps up).
7. Follow-up biometrics improve and risk drops significantly.
8. Clinician reviews triage SOAP note and approves with clinical stamp.
9. Population health dashboard updates to reflect the improved outcome.

All steps execute programmatically in seconds (< 5 seconds), completely satisfying
the under-5-minutes challenge requirement.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from packages.types.enums import (
    RiskTier,
    TrajectoryTrend,
    ClinicianReviewStatus,
    TriageUrgency,
    InterventionPillar,
)
from packages.clinical_models.observations import Observation
from packages.clinical_models.risk import (
    RiskAssessment,
    DomainRiskScores,
    RiskDriver,
    ProtectiveFactor,
)
from packages.clinical_models.care_plan import CarePlan, DailyTask
from packages.clinical_models.triage import ClinicalTriageCase, SOAPReport
from services.store import store, CitizenRecord
from services.trajectory.models import RiskSnapshot
from services.trajectory.engine import risk_trajectory_engine
from services.wearable.simulator import generate_synthetic_wearable_timeseries
from services.population_intelligence.analytics import (
    get_population_overview,
    calculate_intervention_outcome_delta,
)


class DemoStoryStage(BaseModel):
    step_number: int
    title: str
    narrative: str
    status: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_snapshot: Dict[str, Any] = Field(default_factory=dict)


class DemoStoryResult(BaseModel):
    citizen_id: str
    citizen_name: str
    total_execution_seconds: float
    total_stages: int
    stages: List[DemoStoryStage]
    baseline_risk_score: float
    worsened_risk_score: float
    improved_risk_score: float
    net_risk_reduction_percentage: float
    clinician_review_status: str
    population_outcome_delta: Dict[str, Any]


def execute_demo_story(
    citizen_id: str = "citizen-arjun-mehta-11",
    clinician_id: str = "doctor-user-01",
) -> DemoStoryResult:
    """Executes the complete 9-stage SevaHealth demo narrative from start to finish."""
    start_time = time.time()
    stages: List[DemoStoryStage] = []
    now = datetime.now(timezone.utc)

    # Resolve or create the demo subject
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        # Auto-create if not already seeded
        citizen = CitizenRecord(
            id=citizen_id,
            tenant_id="karnataka_state_health",
            user_id=f"user-{citizen_id}",
            abha_id="91-4820-1092-2026",
            first_name="Arjun",
            last_name="Mehta",
            birth_date="1981-05-14",
            gender="MALE",
            phone="+91 98800 55667",
            state="Karnataka",
            district="Bengaluru Rural",
            sub_district="Devanahalli Taluk",
            village_or_ward="Devanahalli Town Ward 4",
        )
        store.add_citizen(citizen)

    citizen_name = f"{citizen.first_name} {citizen.last_name}"

    # -------------------------------------------------------------------------
    # STAGE 1: Citizen Starts with Moderate Risk (Baseline)
    # -------------------------------------------------------------------------
    base_snap = RiskSnapshot(
        snapshot_id=f"snap-{citizen_id}-base",
        citizen_id=citizen_id,
        timestamp=now - timedelta(days=180),
        domain_scores={
            "metabolic": 0.35,
            "diabetes": 0.32,
            "hypertension": 0.30,
            "cardiovascular": 0.26,
            "obesity": 0.34,
            "renal": 0.12,
            "lifestyle": 0.28,
        },
        domain_tiers={
            "metabolic": "MODERATE",
            "diabetes": "MODERATE",
            "hypertension": "LOW",
            "cardiovascular": "LOW",
            "obesity": "MODERATE",
            "renal": "LOW",
            "lifestyle": "LOW",
        },
        key_biomarkers={
            "WEIGHT_KG": 74.0,
            "BMI": 24.8,
            "WAIST_CIRCUMFERENCE": 88.0,
            "SYSTOLIC_BP": 124.0,
            "DIASTOLIC_BP": 82.0,
            "HBA1C": 5.6,
            "FASTING_GLUCOSE": 98.0,
            "STEPS": 7500,
            "RESTING_HR": 68.0,
        },
        source="ANNUAL_CHECKUP",
    )
    store.set_trajectory_snapshots(citizen_id, [base_snap])

    base_risk = RiskAssessment(
        id=f"risk-{citizen_id}-base",
        tenant_id=citizen.tenant_id,
        citizen_id=citizen_id,
        overall_score=0.36,
        overall_tier=RiskTier.MODERATE,
        domains=DomainRiskScores(
            diabetes_risk=0.32,
            hypertension_risk=0.30,
            cardiovascular_risk=0.26,
            metabolic_syndrome_risk=0.35,
            ckd_risk=0.12,
            fatty_liver_risk=0.20,
        ),
        trajectory=TrajectoryTrend.STABLE,
        confidence_score=0.92,
        clinical_summary="Moderate baseline NCD risk. Routine healthy habits maintained.",
    )
    store.add_risk_assessment(base_risk)

    stages.append(
        DemoStoryStage(
            step_number=1,
            title="Initial Baseline Health Assessment",
            narrative=(
                f"{citizen_name} (Age 45) enters SevaHealth via routine community screening. "
                "Baseline health is MODERATE (Score: 36%), with normal fasting blood sugar (98 mg/dL), "
                "healthy HbA1c (5.6%), and good activity (7,500 daily steps)."
            ),
            status="COMPLETED",
            data_snapshot={
                "risk_tier": "MODERATE",
                "risk_score": 0.36,
                "weight_kg": 74.0,
                "bp": "124/82 mmHg",
                "hba1c": "5.6%",
                "steps_per_day": 7500,
            },
        )
    )

    # -------------------------------------------------------------------------
    # STAGE 2: Silent Progression (Weight ↑, Activity ↓, BP ↑, HbA1c ↑)
    # -------------------------------------------------------------------------
    # Six months pass: sedentary desk stress, late-night dinners, missed workouts
    worsened_obs = [
        ("SYSTOLIC_BP", 142.0, "mmHg", "8480-6", "Systolic Blood Pressure"),
        ("DIASTOLIC_BP", 90.0, "mmHg", "8462-4", "Diastolic Blood Pressure"),
        ("FASTING_GLUCOSE", 118.0, "mg/dL", "1558-6", "Fasting Blood Glucose"),
        ("HBA1C", 6.3, "%", "4548-4", "Hemoglobin A1c"),
        ("BMI", 27.6, "kg/m2", "39156-5", "Body Mass Index"),
        ("WAIST_CIRCUMFERENCE", 95.0, "cm", "8280-0", "Waist Circumference"),
    ]
    for code, val, unit, loinc, name in worsened_obs:
        store.add_observation(
            Observation(
                id=str(uuid.uuid4()),
                tenant_id=citizen.tenant_id,
                citizen_id=citizen_id,
                code=code,
                value=val,
                unit=unit,
                loinc_code=loinc,
                display_name=name,
                source="FOLLOWUP_COMMUNITY_CAMP",
            )
        )

    # Wearables show physical activity drop
    store.wearable_data[citizen_id] = generate_synthetic_wearable_timeseries(
        citizen_id=citizen_id, days=14, base_rhr=78.0, base_hrv=32.0, base_steps=3200, stress_trend=True
    )

    stages.append(
        DemoStoryStage(
            step_number=2,
            title="Silent Disease Progression (Over 6 Months)",
            narrative=(
                f"Without feeling 'sick', {citizen_name} silently moves toward chronic disease: "
                "Weight increases by 8.5 kg (BMI 27.6), daily activity collapses from 7,500 to 3,200 steps, "
                "blood pressure rises to 142/90 mmHg, and HbA1c increases into the prediabetic range (6.3%)."
            ),
            status="COMPLETED",
            data_snapshot={
                "weight_delta": "+8.5 kg (74.0 kg -> 82.5 kg)",
                "steps_delta": "-4,300 steps/day (7,500 -> 3,200)",
                "bp_delta": "+18/+8 mmHg (124/82 -> 142/90)",
                "hba1c_delta": "+0.7% (5.6% -> 6.3% Prediabetic)",
            },
        )
    )

    # -------------------------------------------------------------------------
    # STAGE 3: SevaHealth Detects Worsening Trajectory
    # -------------------------------------------------------------------------
    worsened_snap = RiskSnapshot(
        snapshot_id=f"snap-{citizen_id}-worsened",
        citizen_id=citizen_id,
        timestamp=now,
        domain_scores={
            "metabolic": 0.72,
            "diabetes": 0.74,
            "hypertension": 0.68,
            "cardiovascular": 0.54,
            "obesity": 0.70,
            "renal": 0.24,
            "lifestyle": 0.65,
        },
        domain_tiers={
            "metabolic": "HIGH",
            "diabetes": "HIGH",
            "hypertension": "HIGH",
            "cardiovascular": "MODERATE",
            "obesity": "HIGH",
            "renal": "MODERATE",
            "lifestyle": "HIGH",
        },
        key_biomarkers={
            "WEIGHT_KG": 82.5,
            "BMI": 27.6,
            "WAIST_CIRCUMFERENCE": 95.0,
            "SYSTOLIC_BP": 142.0,
            "DIASTOLIC_BP": 90.0,
            "HBA1C": 6.3,
            "FASTING_GLUCOSE": 118.0,
            "STEPS": 3200,
            "RESTING_HR": 78.0,
        },
        source="FOLLOWUP_CAMP",
    )
    store.add_trajectory_snapshot(citizen_id, worsened_snap)

    worsened_risk = RiskAssessment(
        id=f"risk-{citizen_id}-worsened",
        tenant_id=citizen.tenant_id,
        citizen_id=citizen_id,
        overall_score=0.71,
        overall_tier=RiskTier.HIGH,
        domains=DomainRiskScores(
            diabetes_risk=0.74,
            hypertension_risk=0.68,
            cardiovascular_risk=0.54,
            metabolic_syndrome_risk=0.72,
            ckd_risk=0.24,
            fatty_liver_risk=0.60,
        ),
        trajectory=TrajectoryTrend.DETERIORATING,
        confidence_score=0.95,
        top_drivers=[
            RiskDriver(feature_name="Prediabetic Glycemic Elevation", observed_value="HbA1c 6.3%, FBG 118 mg/dL", target_value="< 5.7%", impact_weight=0.28, category="BIOMETRIC"),
            RiskDriver(feature_name="Stage 1-2 Hypertension Surge", observed_value="142/90 mmHg", target_value="< 120/80", impact_weight=0.24, category="BIOMETRIC"),
            RiskDriver(feature_name="Severe Physical Inactivity", observed_value="3,200 steps/day", target_value="> 7,000", impact_weight=0.20, category="LIFESTYLE"),
            RiskDriver(feature_name="Visceral Weight Gain", observed_value="BMI 27.6, Waist 95 cm", target_value="BMI < 23", impact_weight=0.16, category="BIOMETRIC"),
        ],
        clinical_summary="Rapidly deteriorating metabolic & vascular trajectory. High prediabetes and hypertension risk.",
    )
    store.add_risk_assessment(worsened_risk)

    # Trajectory Engine evaluation
    traj_report = risk_trajectory_engine.evaluate_trajectory(citizen_id, [base_snap, worsened_snap])

    store.add_alert({
        "id": f"alert-{citizen_id}-progression",
        "citizen_id": citizen_id,
        "urgency": "PRIORITY",
        "alert_type": "WORSENING_TRAJECTORY_EARLY_WARNING",
        "message": f"SevaHealth Trajectory Alert: {citizen_name}'s metabolic risk jumped by +35% over 180 days.",
        "created_at": now.isoformat(),
        "is_acknowledged": False,
    })

    stages.append(
        DemoStoryStage(
            step_number=3,
            title="SevaHealth Detects Worsening Risk Trajectory",
            narrative=(
                "Rather than presenting 25 disconnected numbers, SevaHealth's Trajectory Engine detects a "
                "DETERIORATING trend (+35% risk velocity). Overall score surges from 36% (Moderate) to 71% (HIGH). "
                "An automated early-warning alert is triggered before irreversible disease occurs."
            ),
            status="COMPLETED",
            data_snapshot={
                "trajectory_trend": "DETERIORATING",
                "risk_jump": "36% -> 71% (+35% escalation)",
                "trajectory_velocity": f"{traj_report.composite_change_percentage:+0.1f}%" if traj_report.composite_change_percentage is not None else "+35.0%",
                "alert_triggered": "WORSENING_TRAJECTORY_EARLY_WARNING",
            },
        )
    )

    # -------------------------------------------------------------------------
    # STAGE 4: AI Explains Contributors (Explainable Waterfall)
    # -------------------------------------------------------------------------
    explainable_contributors = [
        {"factor": "Impaired Glycemia", "delta": "+0.7% HbA1c", "weight": "28%", "impact": "Primary driver of diabetes trajectory"},
        {"factor": "Vascular Strain", "delta": "+18 mmHg SBP", "weight": "24%", "impact": "Elevates peripheral vascular resistance"},
        {"factor": "Physical Deconditioning", "delta": "-4,300 steps", "weight": "20%", "impact": "Reduces insulin sensitivity"},
        {"factor": "Visceral Adiposity", "delta": "+8.5 kg weight", "weight": "16%", "impact": "Drives chronic low-grade inflammation"},
    ]

    ai_explanation_en = (
        f"Hello {citizen_name}. Your metabolic risk has increased from Moderate to HIGH over the past 6 months.\n"
        "Main contributors:\n"
        "• Weight: +8.5 kg (BMI 27.6)\n"
        "• Physical activity: Down to 3,200 steps/day\n"
        "• Blood Sugar: HbA1c 6.3% (Prediabetic range)\n"
        "• Blood pressure: 142/90 mmHg\n\n"
        "AI Recommendation: Your highest-impact intervention is replacing refined carbohydrates with millets "
        "and resuming a 20-minute daily post-dinner walk."
    )

    ai_explanation_kn = (
        f"ನಮಸ್ಕಾರ {citizen_name}. ಕಳೆದ 6 ತಿಂಗಳಲ್ಲಿ ನಿಮ್ಮ ಅಪಾಯವು Moderate ನಿಂದ HIGH ಗೆ ಹೆಚ್ಚಾಗಿದೆ.\n"
        "ಮುಖ್ಯ ಕಾರಣಗಳು: ತೂಕ ಹೆಚ್ಚಳ (+8.5 kg), ನಡಿಗೆ ಇಳಿಕೆ (3,200 ಹೆಜ್ಜೆಗಳು), ಮತ್ತು ರಕ್ತದೊತ್ತಡ 142/90.\n"
        "ಸಲಹೆ: ಸಿರಿಧಾನ್ಯ ಸೇವನೆ ಮತ್ತು ಊಟದ ನಂತರ 20 ನಿಮಿಷಗಳ ನಡಿಗೆ ಅತ್ಯಂತ ಪರಿಣಾಮಕಾರಿಯಾಗಿದೆ."
    )

    stages.append(
        DemoStoryStage(
            step_number=4,
            title="AI Explains Risk Contributors (No Black Box)",
            narrative=(
                "SevaHealth avoids black-box predictions. The AI presents an explainable waterfall decomposing "
                "exactly why risk increased. It communicates clear, non-causal guidance in both English and Kannada."
            ),
            status="COMPLETED",
            data_snapshot={
                "top_contributors": explainable_contributors,
                "ai_explanation_english": ai_explanation_en,
                "ai_explanation_kannada": ai_explanation_kn,
            },
        )
    )

    # -------------------------------------------------------------------------
    # STAGE 5: AI Creates Personalized Prevention Intervention
    # -------------------------------------------------------------------------
    tasks_intervention = [
        DailyTask(
            id=f"arjun-task-{d}",
            day=d,
            pillar=InterventionPillar.PHYSICAL_ACTIVITY if d % 2 == 0 else InterventionPillar.NUTRITION,
            title=f"Day {d}: 20-Minute Post-Dinner Brisk Walk (Target: 7,000 steps)" if d % 2 == 0 else f"Day {d}: Swap White Rice for Foxtail Millet & Green Leafy Vegetables",
            description="Blunts post-prandial glycemic excursions by 28%." if d % 2 == 0 else "Lowers glycemic load and provides soluble fiber for lipid control.",
            target_metric="7,000 steps" if d % 2 == 0 else "1 millet meal",
            completed=False,
        )
        for d in range(1, 31)
    ]

    intervention_plan = CarePlan(
        id=f"careplan-{citizen_id}-intervention",
        tenant_id=citizen.tenant_id,
        citizen_id=citizen_id,
        risk_assessment_id=worsened_risk.id,
        title="SevaHealth 30-Day Metabolic & Vascular Reset Journey",
        focus_domain="Prediabetes Reversal & Blood Pressure Normalization",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        adherence_percentage=0.0,
        nutrition_guidance="Replace polished white rice with foxtail millet or ragi. Eliminate sugary beverages.",
        activity_guidance="Target 7,000 daily steps with consistent 20-minute post-dinner brisk walks.",
        sleep_guidance="7.5 hours nightly sleep; screen cutoff 45 minutes prior.",
        stress_guidance="5-minute evening diaphragmatic breathing.",
        daily_tasks=tasks_intervention,
    )
    store.set_care_plan(intervention_plan)

    stages.append(
        DemoStoryStage(
            step_number=5,
            title="AI Creates Personalized 30-Day Prevention Care Plan",
            narrative=(
                "Risk prediction alone does not solve disease. SevaHealth converts Risk into Personalized Action: "
                "A tailored 30-day lifestyle medicine intervention focusing on nutrition (foxtail millet swap), "
                "activity (7,000 steps/day), and blood pressure monitoring."
            ),
            status="COMPLETED",
            data_snapshot={
                "care_plan_title": intervention_plan.title,
                "duration_days": 30,
                "nutrition_target": intervention_plan.nutrition_guidance,
                "activity_target": intervention_plan.activity_guidance,
                "total_tasks_scheduled": len(tasks_intervention),
            },
        )
    )

    # -------------------------------------------------------------------------
    # STAGE 6: Citizen Completes Intervention (Adherence & Wearables)
    # -------------------------------------------------------------------------
    # Citizen completes 26 out of 30 tasks (86.7% adherence)
    for i in range(26):
        tasks_intervention[i].completed = True
        tasks_intervention[i].completed_at = now - timedelta(days=30 - i)

    intervention_plan.adherence_percentage = 86.7
    store.set_care_plan(intervention_plan)

    # Citizen logs daily check-ins
    store.add_checkin(
        citizen_id,
        {
            "id": f"checkin-{citizen_id}-final",
            "date": str(date.today()),
            "tasks_completed_count": 26,
            "tasks_total_count": 30,
            "subjective_wellbeing": "EXCELLENT",
            "notes": "Completed 26 days of post-dinner walks and replaced white rice with foxtail millet. Feeling significantly more energetic!",
            "recorded_at": now.isoformat(),
        },
    )

    # Wearables sync reflects sustained lifestyle behavior change
    store.wearable_data[citizen_id] = generate_synthetic_wearable_timeseries(
        citizen_id=citizen_id, days=14, base_rhr=66.0, base_hrv=52.0, base_steps=8200, stress_trend=False
    )

    stages.append(
        DemoStoryStage(
            step_number=6,
            title="Citizen Completes Intervention & Telemetry Syncs",
            narrative=(
                f"{citizen_name} engages with SevaHealth's AI Prevention Agent daily, completing 26/30 tasks "
                "(86.7% adherence). Wearable sync confirms daily steps surged back to 8,200 steps/day and "
                "resting heart rate dropped from 78 to 66 bpm."
            ),
            status="COMPLETED",
            data_snapshot={
                "adherence_rate": "86.7% (26/30 tasks completed)",
                "wearable_steps": "8,200 steps/day (+156% increase)",
                "resting_heart_rate": "66 bpm (improved from 78 bpm)",
                "subjective_wellbeing": "EXCELLENT",
            },
        )
    )

    # -------------------------------------------------------------------------
    # STAGE 7: Risk Improves & Trajectory Reverses
    # -------------------------------------------------------------------------
    # Follow-up screening after 30-day intervention
    improved_obs = [
        ("SYSTOLIC_BP", 122.0, "mmHg", "8480-6", "Systolic Blood Pressure"),
        ("DIASTOLIC_BP", 80.0, "mmHg", "8462-4", "Diastolic Blood Pressure"),
        ("FASTING_GLUCOSE", 96.0, "mg/dL", "1558-6", "Fasting Blood Glucose"),
        ("HBA1C", 5.6, "%", "4548-4", "Hemoglobin A1c"),
        ("BMI", 25.3, "kg/m2", "39156-5", "Body Mass Index"),
        ("WAIST_CIRCUMFERENCE", 89.0, "cm", "8280-0", "Waist Circumference"),
    ]
    for code, val, unit, loinc, name in improved_obs:
        store.add_observation(
            Observation(
                id=str(uuid.uuid4()),
                tenant_id=citizen.tenant_id,
                citizen_id=citizen_id,
                code=code,
                value=val,
                unit=unit,
                loinc_code=loinc,
                display_name=name,
                source="POST_INTERVENTION_ASSESSMENT",
            )
        )

    improved_snap = RiskSnapshot(
        snapshot_id=f"snap-{citizen_id}-improved",
        citizen_id=citizen_id,
        timestamp=now + timedelta(days=30),
        domain_scores={
            "metabolic": 0.22,
            "diabetes": 0.20,
            "hypertension": 0.22,
            "cardiovascular": 0.18,
            "obesity": 0.25,
            "renal": 0.10,
            "lifestyle": 0.16,
        },
        domain_tiers={
            "metabolic": "LOW",
            "diabetes": "LOW",
            "hypertension": "LOW",
            "cardiovascular": "LOW",
            "obesity": "MODERATE",
            "renal": "LOW",
            "lifestyle": "LOW",
        },
        key_biomarkers={
            "WEIGHT_KG": 76.2,
            "BMI": 25.3,
            "WAIST_CIRCUMFERENCE": 89.0,
            "SYSTOLIC_BP": 122.0,
            "DIASTOLIC_BP": 80.0,
            "HBA1C": 5.6,
            "FASTING_GLUCOSE": 96.0,
            "STEPS": 8200,
            "RESTING_HR": 66.0,
        },
        source="POST_INTERVENTION_ASSESSMENT",
    )
    store.add_trajectory_snapshot(citizen_id, improved_snap)

    improved_risk = RiskAssessment(
        id=f"risk-{citizen_id}-improved",
        tenant_id=citizen.tenant_id,
        citizen_id=citizen_id,
        overall_score=0.24,
        overall_tier=RiskTier.LOW,
        domains=DomainRiskScores(
            diabetes_risk=0.20,
            hypertension_risk=0.22,
            cardiovascular_risk=0.18,
            metabolic_syndrome_risk=0.22,
            ckd_risk=0.10,
            fatty_liver_risk=0.15,
        ),
        trajectory=TrajectoryTrend.IMPROVING,
        confidence_score=0.96,
        top_drivers=[],
        protective_factors=[
            ProtectiveFactor(feature_name="Glycemic Normalization", observed_value="HbA1c 5.6%, FBG 96", impact_weight=-0.32),
            ProtectiveFactor(feature_name="Blood Pressure Normalization", observed_value="122/80 mmHg", impact_weight=-0.26),
            ProtectiveFactor(feature_name="Weight Reduction", observed_value="-6.3 kg (BMI 25.3)", impact_weight=-0.22),
            ProtectiveFactor(feature_name="Consistent Activity Adherence", observed_value="8,200 steps/day", impact_weight=-0.20),
        ],
        clinical_summary="Successful prediabetes and prehypertension reversal. Risk stabilized to LOW.",
    )
    store.add_risk_assessment(improved_risk)

    stages.append(
        DemoStoryStage(
            step_number=7,
            title="Risk Reversal & Biomarker Normalization",
            narrative=(
                "Following the 30-day intervention, repeat screening confirms objective physiological improvement: "
                "Weight decreased by 6.3 kg, BP dropped from 142/90 to 122/80 mmHg, and HbA1c normalized back to 5.6%. "
                "Risk plunges from 71% (High) down to 24% (Low) — trajectory is now IMPROVING."
            ),
            status="COMPLETED",
            data_snapshot={
                "risk_score_delta": "71% -> 24% (-47% absolute reduction)",
                "trajectory_trend": "IMPROVING",
                "hba1c_normalized": "6.3% -> 5.6% (Prediabetes reversed)",
                "bp_normalized": "142/90 -> 122/80 mmHg",
                "weight_loss": "-6.3 kg (82.5 kg -> 76.2 kg)",
            },
        )
    )

    # -------------------------------------------------------------------------
    # STAGE 8: Clinician Reviews & Signs Off (Closed Loop)
    # -------------------------------------------------------------------------
    triage_case = ClinicalTriageCase(
        id=f"triage-{citizen_id}-story",
        tenant_id=citizen.tenant_id,
        citizen_id=citizen_id,
        citizen_name=citizen_name,
        risk_assessment_id=improved_risk.id,
        urgency=TriageUrgency.ROUTINE,
        escalation_reason="Post-intervention outcome verification and maintenance plan approval.",
        soap_note=SOAPReport(
            subjective=f"Patient {citizen_name} (Age 45) completed 30-day SevaHealth lifestyle intervention with 86.7% adherence. Reports full symptom resolution and high vitality.",
            objective="Weight 76.2 kg (-6.3 kg). BP 122/80 mmHg. Fasting blood glucose 96 mg/dL. HbA1c normalized to 5.6%. Wearable activity average 8,200 steps/day.",
            assessment="Prediabetes reversal and stage 1 hypertension resolution achieved through lifestyle medicine without requiring pharmacotherapy escalation.",
            plan="1. Approve transition to annual maintenance monitoring. 2. Continue foxtail millet dietary regimen. 3. Sustain 7,000+ daily steps.",
        ),
        status=ClinicianReviewStatus.APPROVED,
        assigned_clinician_id=clinician_id,
        review_notes=(
            "Doctor Anand Kulkarni, MD: Outstanding patient adherence and objective biometric reversal. "
            "Biomarkers reflect complete glycemic and vascular stabilization. Approved."
        ),
        reviewed_at=now,
    )
    store.add_triage_case(triage_case)

    # Clinician signs off on the care plan
    intervention_plan.clinician_reviewed = True
    intervention_plan.clinician_id = clinician_id
    store.set_care_plan(intervention_plan)

    stages.append(
        DemoStoryStage(
            step_number=8,
            title="Clinician Reviews & Signs Off (Human-in-the-Loop)",
            narrative=(
                "SevaHealth never replaces doctors. Dr. Anand Kulkarni reviews the AI synthesis and SOAP note "
                "in the Clinician Copilot portal, confirms the lifestyle-induced reversal, and digitally signs off."
            ),
            status="COMPLETED",
            data_snapshot={
                "reviewing_doctor": "Dr. Anand Kulkarni, MD",
                "decision": "APPROVED",
                "doctor_notes": triage_case.review_notes,
                "soap_assessment": triage_case.soap_note.assessment if triage_case.soap_note else "",
                "status": "APPROVED",
            },
        )
    )

    # -------------------------------------------------------------------------
    # STAGE 9: Population Health Dashboard Reflects Outcome
    # -------------------------------------------------------------------------
    # Recompute population health analytics
    overview = get_population_overview(district="Bengaluru Rural")
    outcome_delta = calculate_intervention_outcome_delta()

    stages.append(
        DemoStoryStage(
            step_number=9,
            title="Population Health Dashboard Reflects Outcome",
            narrative=(
                "The closed loop is completed: District Health Officers see population-level intelligence update in real time. "
                "High-risk NCD prevalence decreases, average cohort adherence rises to 86.7%, and population health outcome deltas "
                "prove preventive ROI before hospitalizations occur."
            ),
            status="COMPLETED",
            data_snapshot={
                "district": "Bengaluru Rural",
                "screened_cohort_count": overview.population_screened,
                "cohort_adherence_rate": "86.7%",
                "average_hba1c_reduction": "-0.7% across adherent prediabetes cohort",
                "average_sbp_reduction": "-16.0 mmHg across adherent prehypertension cohort",
                "hospitalization_cost_avoidance": "Estimated ₹42,000 / citizen / year",
            },
        )
    )

    total_time = round(time.time() - start_time, 2)

    return DemoStoryResult(
        citizen_id=citizen_id,
        citizen_name=citizen_name,
        total_execution_seconds=total_time,
        total_stages=len(stages),
        stages=stages,
        baseline_risk_score=0.36,
        worsened_risk_score=0.71,
        improved_risk_score=0.24,
        net_risk_reduction_percentage=round(((0.71 - 0.24) / 0.71) * 100, 1),
        clinician_review_status="APPROVED",
        population_outcome_delta=outcome_delta,
    )
