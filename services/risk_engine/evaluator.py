from typing import Dict, List, Tuple, Optional
from packages.types.enums import RiskTier, TrajectoryTrend
from packages.clinical_models.risk import DomainRiskScores, RiskDriver, ProtectiveFactor
from packages.clinical_models.observations import Observation
from services.wearable.models import WearableProjection


def evaluate_ncd_domains(
    observations: List[Observation],
    idrs_score: int = 40,
    age: int = 45,
    gender: str = "MALE",
    smoker: bool = False,
    wearable_projection: Optional[WearableProjection] = None,
) -> Tuple[DomainRiskScores, float, RiskTier, TrajectoryTrend, List[RiskDriver], List[ProtectiveFactor]]:
    """Evaluates multivariable NCD risk across 6 domains with explainable feature attribution.

    Mathematical guidelines:
    - ICMR-INDIAB Diabetes Criteria
    - AHA/ACC 2017 Blood Pressure Guidelines
    - WHO-SEAR 10-Year Cardiovascular Risk
    - Asian Indian Specific Anthropometrics (BMI >= 23, Waist >= 90M/80F)
    """
    obs_map: Dict[str, float] = {o.code: o.value for o in observations}

    # Extract biomarker values
    sbp = obs_map.get("SYSTOLIC_BP", 125.0)
    dbp = obs_map.get("DIASTOLIC_BP", 82.0)
    fbg = obs_map.get("FASTING_GLUCOSE", 98.0)
    hba1c = obs_map.get("HBA1C", 5.5)
    chol = obs_map.get("TOTAL_CHOLESTEROL", 190.0)
    hdl = obs_map.get("HDL_CHOLESTEROL", 45.0)
    tg = obs_map.get("TRIGLYCERIDES", 140.0)
    bmi = obs_map.get("BMI", 23.5)
    waist = obs_map.get("WAIST_CIRCUMFERENCE", 88.0)
    egfr = obs_map.get("EGFR", 95.0)

    drivers: List[RiskDriver] = []
    protective: List[ProtectiveFactor] = []

    # 1. Diabetes & Prediabetes Risk Calculation
    diabetes_prob = 0.15
    if hba1c >= 6.5 or fbg >= 126.0:
        diabetes_prob = 0.88
        drivers.append(RiskDriver(
            feature_name="Diabetic Threshold Biomarker",
            observed_value=f"HbA1c {hba1c}%, FBG {fbg} mg/dL",
            target_value="HbA1c < 5.7%, FBG < 100 mg/dL",
            impact_weight=0.30,
            category="BIOMETRIC",
            evidence_citation="ICMR Guidelines 2023 / ADA Standards of Care"
        ))
    elif hba1c >= 5.7 or fbg >= 100.0 or idrs_score >= 60:
        diabetes_prob = 0.65
        drivers.append(RiskDriver(
            feature_name="Prediabetic Impaired Glycemia",
            observed_value=f"HbA1c {hba1c}%, IDRS Score {idrs_score}/100",
            target_value="HbA1c < 5.7%, IDRS < 30",
            impact_weight=0.22,
            category="BIOMETRIC",
            evidence_citation="ICMR-INDIAB Prediabetes Criteria"
        ))
    else:
        diabetes_prob = 0.15
        protective.append(ProtectiveFactor(
            feature_name="Optimal Fasting Glucose Control",
            observed_value=f"HbA1c {hba1c}%",
            impact_weight=-0.12,
            category="BIOMETRIC"
        ))

    # 2. Hypertension Risk Calculation
    htn_prob = 0.10
    if sbp >= 160.0 or dbp >= 100.0:
        htn_prob = 0.92
        drivers.append(RiskDriver(
            feature_name="Stage 2 Hypertension (Critical)",
            observed_value=f"{sbp:.0f}/{dbp:.0f} mmHg",
            target_value="< 120/80 mmHg",
            impact_weight=0.28,
            category="BIOMETRIC",
            evidence_citation="ACC/AHA 2017 High Blood Pressure Guidelines"
        ))
    elif sbp >= 130.0 or dbp >= 85.0:
        htn_prob = 0.60
        drivers.append(RiskDriver(
            feature_name="Elevated Vascular Pressure",
            observed_value=f"{sbp:.0f}/{dbp:.0f} mmHg",
            target_value="< 120/80 mmHg",
            impact_weight=0.18,
            category="BIOMETRIC",
            evidence_citation="ACC/AHA 2017 Guidelines"
        ))
    else:
        htn_prob = 0.12
        protective.append(ProtectiveFactor(
            feature_name="Optimal Blood Pressure",
            observed_value=f"{sbp:.0f}/{dbp:.0f} mmHg",
            impact_weight=-0.14,
            category="BIOMETRIC"
        ))

    # 3. Cardiovascular 10-Year ASCVD Risk (WHO-SEAR adapted)
    cvd_prob = 0.10
    cvd_points = 0.0
    if smoker:
        cvd_points += 0.20
        drivers.append(RiskDriver(
            feature_name="Active Tobacco Consumption",
            observed_value="Tobacco user",
            target_value="Complete cessation",
            impact_weight=0.20,
            category="LIFESTYLE",
            evidence_citation="WHO Cardiovascular Disease Risk Charts"
        ))
    else:
        protective.append(ProtectiveFactor(
            feature_name="Tobacco Abstinence",
            observed_value="Non-smoker",
            impact_weight=-0.15,
            category="LIFESTYLE"
        ))

    if chol >= 240.0:
        cvd_points += 0.25
        drivers.append(RiskDriver(
            feature_name="Elevated Total Serum Cholesterol",
            observed_value=f"{chol:.0f} mg/dL",
            target_value="< 200 mg/dL",
            impact_weight=0.18,
            category="BIOMETRIC",
            evidence_citation="NCEP ATP III / ACC Lipid Guidelines"
        ))
    cvd_prob = min(0.95, cvd_points + (htn_prob * 0.4) + (diabetes_prob * 0.3))

    # 4. Metabolic Syndrome & Obesity Risk
    metabolic_prob = 0.15
    waist_cutoff = 90.0 if gender == "MALE" else 80.0
    if waist >= waist_cutoff:
        metabolic_prob += 0.30
        drivers.append(RiskDriver(
            feature_name="Visceral Adiposity / Central Obesity",
            observed_value=f"Waist {waist:.0f} cm",
            target_value=f"< {waist_cutoff:.0f} cm (Asian Indian standard)",
            impact_weight=0.16,
            category="BIOMETRIC",
            evidence_citation="ICMR Guidelines on Central Obesity in South Asians"
        ))
    if bmi >= 25.0:
        metabolic_prob += 0.25
        drivers.append(RiskDriver(
            feature_name="Elevated Body Mass Index",
            observed_value=f"BMI {bmi:.1f} kg/m²",
            target_value="< 23.0 kg/m²",
            impact_weight=0.14,
            category="BIOMETRIC",
            evidence_citation="WHO South Asian BMI Cutoff"
        ))
    if tg >= 150.0:
        metabolic_prob += 0.20
    metabolic_prob = min(0.95, metabolic_prob)

    # 5. CKD Risk
    ckd_prob = 0.08
    if egfr < 60.0:
        ckd_prob = 0.75
        drivers.append(RiskDriver(
            feature_name="Reduced Glomerular Filtration Rate",
            observed_value=f"eGFR {egfr:.0f} mL/min/1.73m²",
            target_value=">= 90 mL/min/1.73m²",
            impact_weight=0.25,
            category="BIOMETRIC",
            evidence_citation="KDIGO Chronic Kidney Disease Evaluation"
        ))
    elif diabetes_prob > 0.6 or htn_prob > 0.6:
        ckd_prob = 0.35

    # 6. Fatty Liver (MASLD/NAFLD Surrogate)
    fatty_liver_prob = min(0.90, (metabolic_prob * 0.6) + (diabetes_prob * 0.3))

    domains = DomainRiskScores(
        diabetes_risk=round(diabetes_prob, 2),
        hypertension_risk=round(htn_prob, 2),
        cardiovascular_risk=round(cvd_prob, 2),
        metabolic_syndrome_risk=round(metabolic_prob, 2),
        ckd_risk=round(ckd_prob, 2),
        fatty_liver_risk=round(fatty_liver_prob, 2),
    )

    # Composite Overall Score (Weighted combination)
    overall_score = round(
        (diabetes_prob * 0.25) +
        (htn_prob * 0.25) +
        (cvd_prob * 0.25) +
        (metabolic_prob * 0.15) +
        (ckd_prob * 0.05) +
        (fatty_liver_prob * 0.05),
        2
    )

    # Determine Tier
    if overall_score >= 0.75 or sbp >= 160.0 or diabetes_prob >= 0.85 or htn_prob >= 0.90:
        tier = RiskTier.CRITICAL
        trajectory = TrajectoryTrend.DETERIORATING
    elif overall_score >= 0.50 or diabetes_prob >= 0.60 or htn_prob >= 0.60:
        tier = RiskTier.HIGH
        trajectory = TrajectoryTrend.DETERIORATING
    elif overall_score >= 0.30 or diabetes_prob >= 0.35 or htn_prob >= 0.35:
        tier = RiskTier.MODERATE
        trajectory = TrajectoryTrend.STABLE
    else:
        tier = RiskTier.LOW
        trajectory = TrajectoryTrend.IMPROVING

    # Wearable Physiological Modulation (Consumer Health Telemetry)
    # Never assumed to be clinically equivalent to diagnostic medical measurements.
    # Modulates trajectory velocity and surfaces actionable lifestyle risk/protective factors.
    if wearable_projection:
        if (
            wearable_projection.hrv_suppression_flag
            or wearable_projection.rhr_trend_delta >= 3.0
            or wearable_projection.chronic_sleep_deficit
        ):
            drivers.append(RiskDriver(
                feature_name="Autonomic Strain & Chronic Sleep Deficit",
                observed_value=(
                    f"RHR Δ {wearable_projection.rhr_trend_delta:+.1f} bpm, "
                    f"HRV rMSSD {wearable_projection.avg_hrv_rmssd:.0f} ms (suppressed), "
                    f"Sleep {wearable_projection.avg_sleep_duration_hours:.1f} hrs/day"
                ),
                target_value="RHR Δ <= 0 bpm, HRV >= 45 ms, Sleep >= 7.0 hrs",
                impact_weight=0.15,
                category="LIFESTYLE",
                evidence_citation="Wearable Autonomic Metric Consensus (Consumer-grade signal, non-diagnostic)"
            ))
            if trajectory in [TrajectoryTrend.STABLE, TrajectoryTrend.IMPROVING]:
                trajectory = TrajectoryTrend.DETERIORATING

        elif (
            wearable_projection.step_target_adherence_pct >= 85.0
            and not wearable_projection.hrv_suppression_flag
            and (wearable_projection.rhr_trend_delta <= -0.5 or wearable_projection.avg_daily_steps >= 8000)
        ):
            protective.append(ProtectiveFactor(
                feature_name="Cardiorespiratory Activity Adherence",
                observed_value=(
                    f"{wearable_projection.avg_daily_steps} steps/day "
                    f"({wearable_projection.step_target_adherence_pct:.0f}% goal), "
                    f"RHR Δ {wearable_projection.rhr_trend_delta:+.1f} bpm"
                ),
                impact_weight=-0.12,
                category="LIFESTYLE"
            ))
            if trajectory == TrajectoryTrend.STABLE:
                trajectory = TrajectoryTrend.IMPROVING

    return domains, overall_score, tier, trajectory, drivers, protective
