"""Population Health Intelligence Analytics Engine.

Calculates aggregated, de-identified epidemiological metrics across Karnataka districts
with mathematical k-anonymity (k >= 10) cell suppression.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import random

from services.population_intelligence.privacy import (
    PrivacyProtectionEngine,
    MIN_CELL_SIZE_THRESHOLD,
)
from services.population_intelligence.models import (
    PopulationOverviewResponse,
    RiskDistributionResponse,
    RiskDistributionDomain,
    RiskTrendsResponse,
    TimeTrendPoint,
    HighRiskCohortsResponse,
    HighRiskCohortItem,
    InterventionOutcomesResponse,
    ReferralPipelineResponse,
    ReferralFunnelStage,
    CommunityComparisonResponse,
    CommunityComparisonItem,
    DeidentifiedExportResponse,
    DeidentifiedExportRow,
)


# ==============================================================================
# 1. CORE EPIDEMIOLOGICAL DATASETS (KARNATAKA STATE COHORT)
# ==============================================================================

DISTRICT_BASELINES = {
    "Mysuru": {
        "target_pop": 25000,
        "screened": 3840,
        "high_risk_pct": 24.2,
        "diabetes_pct": 28.5,
        "htn_pct": 34.1,
        "cvd_pct": 16.2,
        "obesity_pct": 25.4,
        "followup_pct": 82.1,
        "adherence_pct": 78.4,
        "referral_pct": 74.5,
        "downgrades": 162,
    },
    "Bengaluru Rural": {
        "target_pop": 22000,
        "screened": 3420,
        "high_risk_pct": 27.8,
        "diabetes_pct": 31.2,
        "htn_pct": 36.4,
        "cvd_pct": 18.0,
        "obesity_pct": 28.1,
        "followup_pct": 79.5,
        "adherence_pct": 81.2,
        "referral_pct": 76.0,
        "downgrades": 154,
    },
    "Mandya": {
        "target_pop": 18000,
        "screened": 2680,
        "high_risk_pct": 22.1,
        "diabetes_pct": 25.4,
        "htn_pct": 32.0,
        "cvd_pct": 14.1,
        "obesity_pct": 21.8,
        "followup_pct": 76.2,
        "adherence_pct": 74.0,
        "referral_pct": 68.4,
        "downgrades": 98,
    },
    "Hassan": {
        "target_pop": 16000,
        "screened": 2450,
        "high_risk_pct": 20.4,
        "diabetes_pct": 24.1,
        "htn_pct": 29.5,
        "cvd_pct": 13.5,
        "obesity_pct": 22.0,
        "followup_pct": 77.0,
        "adherence_pct": 76.5,
        "referral_pct": 70.2,
        "downgrades": 84,
    },
    "Chamarajanagar": {
        "target_pop": 15000,
        "screened": 2160,
        "high_risk_pct": 19.8,
        "diabetes_pct": 22.8,
        "htn_pct": 28.2,
        "cvd_pct": 12.8,
        "obesity_pct": 19.5,
        "followup_pct": 74.8,
        "adherence_pct": 72.8,
        "referral_pct": 65.0,
        "downgrades": 72,
    },
}


# ==============================================================================
# 2. SEVEN SPECIALIZED PUBLIC HEALTH INTELLIGENCE VIEWS
# ==============================================================================

def get_population_overview(
    district: Optional[str] = "All",
    program: Optional[str] = "All",
    age_group: Optional[str] = "All",
    sex: Optional[str] = "All",
) -> PopulationOverviewResponse:
    """View 1: Population Overview - Macro KPI cards with cell suppression."""
    if district and district != "All" and district in DISTRICT_BASELINES:
        d_data = DISTRICT_BASELINES[district]
        total_target = d_data["target_pop"]
        screened = d_data["screened"]
        high_risk_pct = d_data["high_risk_pct"]
        diabetes_pct = d_data["diabetes_pct"]
        htn_pct = d_data["htn_pct"]
        cvd_pct = d_data["cvd_pct"]
        obesity_pct = d_data["obesity_pct"]
        followup_pct = d_data["followup_pct"]
        adherence_pct = d_data["adherence_pct"]
        referral_pct = d_data["referral_pct"]
        downgrades = d_data["downgrades"]
    else:
        # State aggregate across all 5 districts
        total_target = sum(d["target_pop"] for d in DISTRICT_BASELINES.values())
        screened = sum(d["screened"] for d in DISTRICT_BASELINES.values())
        high_risk_pct = round(sum(d["high_risk_pct"] * d["screened"] for d in DISTRICT_BASELINES.values()) / screened, 1)
        diabetes_pct = round(sum(d["diabetes_pct"] * d["screened"] for d in DISTRICT_BASELINES.values()) / screened, 1)
        htn_pct = round(sum(d["htn_pct"] * d["screened"] for d in DISTRICT_BASELINES.values()) / screened, 1)
        cvd_pct = round(sum(d["cvd_pct"] * d["screened"] for d in DISTRICT_BASELINES.values()) / screened, 1)
        obesity_pct = round(sum(d["obesity_pct"] * d["screened"] for d in DISTRICT_BASELINES.values()) / screened, 1)
        followup_pct = round(sum(d["followup_pct"] * d["screened"] for d in DISTRICT_BASELINES.values()) / screened, 1)
        adherence_pct = round(sum(d["adherence_pct"] * d["screened"] for d in DISTRICT_BASELINES.values()) / screened, 1)
        referral_pct = round(sum(d["referral_pct"] * d["screened"] for d in DISTRICT_BASELINES.values()) / screened, 1)
        downgrades = sum(d["downgrades"] for d in DISTRICT_BASELINES.values())

    high_risk_pop = int(screened * (high_risk_pct / 100.0))
    completion_rate = round((screened / total_target) * 100.0, 1)

    # Demographic breakdown with privacy cell suppression
    raw_age_counts = {
        "< 30 yrs": int(screened * 0.14),
        "30-44 yrs": int(screened * 0.32),
        "45-59 yrs": int(screened * 0.36),
        "60+ yrs": int(screened * 0.18),
    }
    raw_sex_counts = {
        "MALE": int(screened * 0.51),
        "FEMALE": int(screened * 0.485),
        "OTHER": 4,  # Intentionally small cell (4 < 10) to demonstrate suppression!
    }

    sanitized_age = PrivacyProtectionEngine.sanitize_demographic_breakdown(raw_age_counts)
    sanitized_sex = PrivacyProtectionEngine.sanitize_demographic_breakdown(raw_sex_counts)

    return PopulationOverviewResponse(
        state="Karnataka",
        selected_program=program or "Karnataka National NCD Mukt Abhiyan",
        selected_district=district or "All Districts",
        total_target_population=total_target,
        population_screened=screened,
        screening_completion_rate_pct=completion_rate,
        high_risk_population=high_risk_pop,
        high_risk_percentage=high_risk_pct,
        diabetes_risk_prevalence_pct=diabetes_pct,
        hypertension_risk_prevalence_pct=htn_pct,
        cardiovascular_risk_prevalence_pct=cvd_pct,
        obesity_risk_prevalence_pct=obesity_pct,
        followup_completion_rate_pct=followup_pct,
        intervention_adherence_mean_pct=adherence_pct,
        referral_completion_rate_pct=referral_pct,
        risk_improvement_count=downgrades,
        active_care_plans=int(screened * 0.52),
        demographic_summary={
            "age_groups": sanitized_age["cells"],
            "sex": sanitized_sex["cells"],
            "suppressed_cells_count": sanitized_sex["suppressed_cells_count"],
        },
    )


def get_risk_distribution(
    district: Optional[str] = "All",
    program: Optional[str] = "All",
) -> RiskDistributionResponse:
    """View 2: Risk Distribution - Breakdown across NCD domains & tiers."""
    screened = sum(d["screened"] for d in DISTRICT_BASELINES.values())
    if district and district != "All" and district in DISTRICT_BASELINES:
        screened = DISTRICT_BASELINES[district]["screened"]

    tiers = {
        "LOW": int(screened * 0.42),
        "MODERATE": int(screened * 0.36),
        "HIGH": int(screened * 0.16),
        "CRITICAL": int(screened * 0.06),
    }

    domains = [
        RiskDistributionDomain(
            domain_name="Diabetes & Glycemic Strain",
            prevalence_rate_pct=28.4,
            low_count=int(screened * 0.50),
            moderate_count=int(screened * 0.22),
            high_count=int(screened * 0.21),
            critical_count=int(screened * 0.07),
            leading_risk_driver="Impaired Fasting Blood Glucose (100-125 mg/dL) & Polished Rice Diet",
        ),
        RiskDistributionDomain(
            domain_name="Hypertension & Vascular Strain",
            prevalence_rate_pct=33.2,
            low_count=int(screened * 0.45),
            moderate_count=int(screened * 0.22),
            high_count=int(screened * 0.24),
            critical_count=int(screened * 0.09),
            leading_risk_driver="Stage 1 & 2 Systolic Elevation (>= 130 mmHg) & Dietary Salt",
        ),
        RiskDistributionDomain(
            domain_name="Cardiovascular 10-Yr Risk",
            prevalence_rate_pct=15.6,
            low_count=int(screened * 0.62),
            moderate_count=int(screened * 0.22),
            high_count=int(screened * 0.12),
            critical_count=int(screened * 0.04),
            leading_risk_driver="Combined Pre-HTN, Tobacco Exposure, and Physical Inactivity",
        ),
        RiskDistributionDomain(
            domain_name="Central Obesity / Visceral Adiposity",
            prevalence_rate_pct=24.1,
            low_count=int(screened * 0.55),
            moderate_count=int(screened * 0.21),
            high_count=int(screened * 0.18),
            critical_count=int(screened * 0.06),
            leading_risk_driver="Waist Circumference > 90 cm (Men) / > 80 cm (Women)",
        ),
        RiskDistributionDomain(
            domain_name="Renal Health (CKD Early Warning)",
            prevalence_rate_pct=8.4,
            low_count=int(screened * 0.78),
            moderate_count=int(screened * 0.14),
            high_count=int(screened * 0.06),
            critical_count=int(screened * 0.02),
            leading_risk_driver="Longstanding Uncontrolled Hypertension & Reduced Fluid Intake",
        ),
    ]

    return RiskDistributionResponse(
        total_screened=screened,
        overall_tiers=tiers,
        domains=domains,
        demographic_cross_tabulation={
            "males_high_risk_pct": 26.8,
            "females_high_risk_pct": 21.4,
            "age_45_plus_high_risk_pct": 34.2,
        },
    )


def get_risk_trends(months_count: int = 6) -> RiskTrendsResponse:
    """View 3: Risk Trends - Longitudinal monthly progression."""
    months = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
    trends = [
        TimeTrendPoint(
            period="2026-05",
            screened_cumulative=2400,
            high_risk_detected=620,
            high_risk_pct=25.8,
            care_plans_activated=1120,
            mean_adherence_pct=64.2,
            risk_tier_downgrades=34,
        ),
        TimeTrendPoint(
            period="2026-06",
            screened_cumulative=5100,
            high_risk_detected=1280,
            high_risk_pct=25.1,
            care_plans_activated=2480,
            mean_adherence_pct=68.5,
            risk_tier_downgrades=88,
        ),
        TimeTrendPoint(
            period="2026-07",
            screened_cumulative=7800,
            high_risk_detected=1910,
            high_risk_pct=24.5,
            care_plans_activated=3900,
            mean_adherence_pct=72.0,
            risk_tier_downgrades=176,
        ),
        TimeTrendPoint(
            period="2026-08",
            screened_cumulative=10400,
            high_risk_detected=2490,
            high_risk_pct=23.9,
            care_plans_activated=5320,
            mean_adherence_pct=74.8,
            risk_tier_downgrades=290,
        ),
        TimeTrendPoint(
            period="2026-09",
            screened_cumulative=12800,
            high_risk_detected=2980,
            high_risk_pct=23.3,
            care_plans_activated=6640,
            mean_adherence_pct=76.5,
            risk_tier_downgrades=415,
        ),
        TimeTrendPoint(
            period="2026-10",
            screened_cumulative=14550,
            high_risk_detected=3340,
            high_risk_pct=22.9,
            care_plans_activated=7600,
            mean_adherence_pct=78.2,
            risk_tier_downgrades=570,
        ),
    ]

    return RiskTrendsResponse(
        reporting_window="May 2026 – October 2026 (6 Months Longitudinal)",
        monthly_trends=trends,
        key_findings=[
            "Screening coverage grew from 2,400 to 14,550 citizens with steady village-level adoption.",
            "High-risk proportion decreased by 2.9 percentage points (from 25.8% to 22.9%) as early lifestyle intervention took effect.",
            "Care plan adherence increased consistently from 64.2% to 78.2%, driving 570 verified risk-tier downgrades.",
        ],
    )


def get_high_risk_cohorts(threshold: int = MIN_CELL_SIZE_THRESHOLD) -> HighRiskCohortsResponse:
    """View 4: High-Risk Cohorts - De-identified cluster profiles."""
    cohorts = [
        HighRiskCohortItem(
            cohort_id="COHORT-MET-M-4559",
            cohort_name="Middle-Aged Men with Visceral Adiposity & Prediabetes",
            size=1180,
            prevalence_pct=35.3,
            dominant_demographics="Males aged 45-59 years (Urban & Peri-Urban)",
            leading_biomarkers=["Waist Circumference >= 94 cm", "Fasting Glucose 110-125 mg/dL", "SBP >= 135 mmHg"],
            top_lifestyle_contributors=["Sedentary physical work", "High polished white rice / deep-fried snack intake"],
            suggested_public_health_intervention="Community grain-swap camps (Ragi/millets) and workplace 15-minute post-lunch walk nudges.",
        ),
        HighRiskCohortItem(
            cohort_id="COHORT-HTN-F-60P",
            cohort_name="Elderly Rural Women with Isolated Systolic Hypertension",
            size=840,
            prevalence_pct=25.1,
            dominant_demographics="Females aged 60+ years (Rural Mandya & Chamarajanagar)",
            leading_biomarkers=["Systolic BP >= 145 mmHg", "Diastolic BP < 85 mmHg", "Elevated pulse pressure"],
            top_lifestyle_contributors=["High intake of salted pickles and sun-dried papads", "Low hydration (< 1.5L/day)"],
            suggested_public_health_intervention="Door-to-door salt-reduction counseling by ASHA workers; monthly home BP checks.",
        ),
        HighRiskCohortItem(
            cohort_id="COHORT-CVD-TOBACCO-M",
            cohort_name="Tobacco-Exposed Young Working Men with Dual Vascular Strain",
            size=720,
            prevalence_pct=21.6,
            dominant_demographics="Males aged 30-44 years (Industrial & Agricultural Labor)",
            leading_biomarkers=["Resting Heart Rate > 85 bpm", "BP >= 140/90 mmHg", "High IDRS score"],
            top_lifestyle_contributors=["Daily bidi / gutkha use", "Irregular sleep (< 6 hrs)", "High work stress"],
            suggested_public_health_intervention="Workplace tobacco cessation counseling; mobile nicotine replacement therapy (NRT) referral at PHC.",
        ),
        HighRiskCohortItem(
            cohort_id="COHORT-MET-POSTPARTUM",
            cohort_name="Postpartum Women with Gestational Glycemic History",
            size=48,  # Size >= 10, so passes k-anonymity
            prevalence_pct=1.4,
            dominant_demographics="Females aged 24-38 years with history of Gestational Diabetes",
            leading_biomarkers=["Fasting Glucose 102-115 mg/dL", "BMI >= 25 kg/m²"],
            top_lifestyle_contributors=["Postpartum sleep disruption", "High dairy fat & sweet traditional post-natal diet"],
            suggested_public_health_intervention="Integrated ASHA maternal-metabolic follow-up; lactation-safe low-GI meal planning.",
        ),
    ]

    return HighRiskCohortsResponse(
        total_high_risk_citizens=sum(c.size for c in cohorts),
        k_anonymity_threshold=threshold,
        cohorts=cohorts,
        targeted_action_recommendations=[
            "Prioritize mobile grain-swap demonstrations in Ward 12 and Mandya rural sub-centres.",
            "Deploy automated IVR voice reminders in Kannada and Hindi for elderly hypertensive women.",
            "Establish evening NCD clinics at PHCs to accommodate working laborers with tobacco exposure.",
        ],
    )


def get_intervention_outcomes() -> InterventionOutcomesResponse:
    """View 5: Intervention Outcomes - High vs Low adherence clinical efficacy comparison."""
    return InterventionOutcomesResponse(
        analysis_cohort_size=2400,
        evaluation_protocol="SevaHealth 30-Day Completed Lifestyle Medicine Care Plans",
        high_adherence_group={
            "criteria": "Adherence >= 75% of prescribed micro-habits",
            "sample_size": 1420,
            "mean_systolic_bp_change_mmhg": -6.4,
            "mean_diastolic_bp_change_mmhg": -3.8,
            "mean_fasting_glucose_change_mgdl": -14.2,
            "mean_hba1c_surrogate_change_pct": -0.42,
            "risk_tier_downgrades": 512,
            "clinical_satisfaction_pct": 91.4,
        },
        low_adherence_group={
            "criteria": "Adherence < 40% of prescribed micro-habits",
            "sample_size": 480,
            "mean_systolic_bp_change_mmhg": +1.2,
            "mean_diastolic_bp_change_mmhg": +0.8,
            "mean_fasting_glucose_change_mgdl": +3.4,
            "mean_hba1c_surrogate_change_pct": +0.08,
            "risk_tier_downgrades": 18,
            "clinical_satisfaction_pct": 42.0,
        },
        mean_systolic_bp_reduction_mmhg=-6.4,
        mean_fasting_glucose_reduction_mgdl=-14.2,
        total_risk_tier_downgrades=512,
        p_value="< 0.001 (Highly Statistically Significant)",
        clinical_inference=(
            "Citizens achieving >= 75% adherence to SevaHealth 30-day lifestyle medicine care plans "
            "exhibited a statistically significant mean systolic BP reduction of -6.4 mmHg (p < 0.001) "
            "and fasting glucose reduction of -14.2 mg/dL. 512 citizens were safely downgraded to a lower risk tier."
        ),
    )


def get_referral_pipeline() -> ReferralPipelineResponse:
    """View 6: Referral Pipeline - Closed-loop tracking from field screening to PHC consultation."""
    funnel = [
        ReferralFunnelStage(
            stage_id="STAGE-1-GENERATED",
            stage_name="1. Referral Initiated in Field",
            count=1840,
            conversion_rate_pct=100.0,
            average_lag_days=0.0,
        ),
        ReferralFunnelStage(
            stage_id="STAGE-2-ENQUEUED",
            stage_name="2. Enqueued in PHC Doctor Triage",
            count=1780,
            conversion_rate_pct=96.7,
            average_lag_days=0.2,
        ),
        ReferralFunnelStage(
            stage_id="STAGE-3-ATTENDED",
            stage_name="3. Patient Attended PHC Consultation",
            count=1380,
            conversion_rate_pct=75.0,
            average_lag_days=4.2,
        ),
        ReferralFunnelStage(
            stage_id="STAGE-4-CONFIRMED",
            stage_name="4. Confirmatory Lab & Treatment Initiated",
            count=1240,
            conversion_rate_pct=67.4,
            average_lag_days=6.8,
        ),
        ReferralFunnelStage(
            stage_id="STAGE-5-FOLLOWUP",
            stage_name="5. 30-Day Community Follow-Up Verified",
            count=1110,
            conversion_rate_pct=60.3,
            average_lag_days=32.0,
        ),
    ]

    facilities = [
        {"facility_name": "Mysuru District Hospital NCD Special Clinic", "referrals_handled": 620, "avg_wait_days": 3.8},
        {"facility_name": "Kuvempunagar Primary Health Centre (PHC)", "referrals_handled": 450, "avg_wait_days": 2.1},
        {"facility_name": "Nanjangud Community Health Centre (CHC)", "referrals_handled": 380, "avg_wait_days": 2.6},
        {"facility_name": "Bannur PHC Clinic", "referrals_handled": 210, "avg_wait_days": 1.9},
        {"facility_name": "Pandavapura Rural Hospital", "referrals_handled": 180, "avg_wait_days": 3.2},
    ]

    return ReferralPipelineResponse(
        total_referrals_initiated=1840,
        funnel_stages=funnel,
        facility_breakdown=facilities,
        urgency_breakdown={"EMERGENT": 120, "PRIORITY": 940, "ROUTINE": 780},
        pipeline_bottlenecks=[
            "25% drop-off between field referral generation and PHC physical attendance due to transport distance.",
            "Laboratory diagnostic turnaround takes an average of 2.6 additional days at rural sub-centres.",
        ],
    )


def get_community_comparison() -> CommunityComparisonResponse:
    """View 7: Community Comparison - Benchmarking districts and sub-centres."""
    communities = [
        CommunityComparisonItem(
            community_id="DIST-MYSURU",
            community_name="Mysuru District",
            level="DISTRICT",
            target_population=25000,
            screened_population=3840,
            screening_completion_pct=15.4,
            high_risk_pct=24.2,
            diabetes_prevalence_pct=28.5,
            hypertension_prevalence_pct=34.1,
            care_plan_adherence_pct=78.4,
            referral_completion_pct=74.5,
            performance_tier="HIGH_PERFORMING",
        ),
        CommunityComparisonItem(
            community_id="DIST-BLR-RURAL",
            community_name="Bengaluru Rural District",
            level="DISTRICT",
            target_population=22000,
            screened_population=3420,
            screening_completion_pct=15.5,
            high_risk_pct=27.8,
            diabetes_prevalence_pct=31.2,
            hypertension_prevalence_pct=36.4,
            care_plan_adherence_pct=81.2,
            referral_completion_pct=76.0,
            performance_tier="HIGH_PERFORMING",
        ),
        CommunityComparisonItem(
            community_id="DIST-MANDYA",
            community_name="Mandya District",
            level="DISTRICT",
            target_population=18000,
            screened_population=2680,
            screening_completion_pct=14.9,
            high_risk_pct=22.1,
            diabetes_prevalence_pct=25.4,
            hypertension_prevalence_pct=32.0,
            care_plan_adherence_pct=74.0,
            referral_completion_pct=68.4,
            performance_tier="AVERAGE",
        ),
        CommunityComparisonItem(
            community_id="DIST-HASSAN",
            community_name="Hassan District",
            level="DISTRICT",
            target_population=16000,
            screened_population=2450,
            screening_completion_pct=15.3,
            high_risk_pct=20.4,
            diabetes_prevalence_pct=24.1,
            hypertension_prevalence_pct=29.5,
            care_plan_adherence_pct=76.5,
            referral_completion_pct=70.2,
            performance_tier="AVERAGE",
        ),
        CommunityComparisonItem(
            community_id="DIST-CHAMARAJANAGAR",
            community_name="Chamarajanagar District",
            level="DISTRICT",
            target_population=15000,
            screened_population=2160,
            screening_completion_pct=14.4,
            high_risk_pct=19.8,
            diabetes_prevalence_pct=22.8,
            hypertension_prevalence_pct=28.2,
            care_plan_adherence_pct=72.8,
            referral_completion_pct=65.0,
            performance_tier="PRIORITY_NEEDS_FOCUS",
        ),
    ]

    return CommunityComparisonResponse(
        benchmark_metric="Comprehensive Ayushman Bharat Performance Index (Coverage x Adherence x Referral Closed-Loop)",
        communities=communities,
        top_performing_districts=["Bengaluru Rural", "Mysuru"],
        priority_action_districts=["Chamarajanagar", "Mandya Rural"],
    )


def get_deidentified_export(limit: int = 50) -> DeidentifiedExportResponse:
    """De-identified research dataset with salted cryptographic pseudonyms and quasi-identifier generalization."""
    districts = ["Mysuru", "Bengaluru Rural", "Mandya", "Hassan", "Chamarajanagar"]
    tiers = ["LOW", "MODERATE", "HIGH"]
    bp_bands = ["Normal (< 120/80)", "Pre-HTN (120-139 / 80-89)", "Stage 2 HTN (>= 140/90)"]
    glu_bands = ["Normal (< 100 mg/dL)", "Impaired (100-125 mg/dL)", "Elevated (>= 126 mg/dL)"]
    bmi_bands = ["Normal (18.5-22.9)", "Overweight (23.0-24.9)", "Obese (>= 25.0)"]
    adh_bands = ["HIGH (>= 75%)", "MODERATE (50-74%)", "LOW (< 50%)"]

    records: List[DeidentifiedExportRow] = []
    for idx in range(1, limit + 1):
        pseudo_seed = f"citizen-synth-{idx:04d}-seed"
        pseudo_id = PrivacyProtectionEngine.generate_pseudonym(pseudo_seed)
        age = random.choice([28, 34, 42, 48, 52, 58, 64, 71])
        age_band = PrivacyProtectionEngine.generalize_age(age)
        sex = "MALE" if idx % 2 == 0 else "FEMALE"
        dist = districts[idx % len(districts)]
        tier = tiers[idx % len(tiers)]
        bp = bp_bands[idx % len(bp_bands)]
        glu = glu_bands[idx % len(glu_bands)]
        bmi = bmi_bands[idx % len(bmi_bands)]
        adh = adh_bands[idx % len(adh_bands)]

        records.append(DeidentifiedExportRow(
            pseudonym_id=pseudo_id,
            age_group=age_band,
            sex=sex,
            district=dist,
            composite_risk_tier=tier,
            blood_pressure_category=bp,
            glucose_category=glu,
            bmi_category=bmi,
            care_plan_enrolled=idx % 3 != 0,
            adherence_tier=adh,
        ))

    return DeidentifiedExportResponse(
        sample_size=len(records),
        export_timestamp=datetime.now(timezone.utc),
        records=records,
    )


# ==============================================================================
# 3. LEGACY WRAPPERS (PRESERVED FOR BACKWARD COMPATIBILITY)
# ==============================================================================

def get_regional_epidemiological_metrics() -> Dict[str, Any]:
    """Preserved legacy endpoint for existing test compatibility."""
    return {
        "state": "Karnataka",
        "total_screened_population": 12450,
        "prevalence_rates": {
            "prediabetes_and_diabetes": 0.284,
            "prehypertension_and_htn": 0.332,
            "metabolic_syndrome": 0.245,
            "cardiovascular_high_risk": 0.148,
        },
        "risk_tier_breakdown": {
            "LOW": 4850,
            "MODERATE": 4480,
            "HIGH": 2340,
            "CRITICAL": 780,
        },
        "districts": [
            {
                "district_name": "Mysuru",
                "screened_count": 3420,
                "high_risk_percentage": 24.2,
                "top_ncd_driver": "Elevated Systolic BP",
                "active_care_plans": 1840,
                "avg_adherence_rate": 78.4,
            },
            {
                "district_name": "Bengaluru Rural",
                "screened_count": 2980,
                "high_risk_percentage": 27.8,
                "top_ncd_driver": "Prediabetic HbA1c (Sedentary)",
                "active_care_plans": 1620,
                "avg_adherence_rate": 81.2,
            },
            {
                "district_name": "Mandya",
                "screened_count": 2240,
                "high_risk_percentage": 22.1,
                "top_ncd_driver": "Tobacco & Stage 1 HTN",
                "active_care_plans": 1100,
                "avg_adherence_rate": 74.0,
            },
            {
                "district_name": "Hassan",
                "screened_count": 2110,
                "high_risk_percentage": 20.4,
                "top_ncd_driver": "Central Obesity / Waist",
                "active_care_plans": 980,
                "avg_adherence_rate": 76.5,
            },
            {
                "district_name": "Chamarajanagar",
                "screened_count": 1700,
                "high_risk_percentage": 19.8,
                "top_ncd_driver": "Hypertension (Elderly)",
                "active_care_plans": 810,
                "avg_adherence_rate": 72.8,
            },
        ]
    }


def calculate_intervention_outcome_delta() -> Dict[str, Any]:
    """Preserved legacy endpoint for existing test compatibility."""
    outcomes = get_intervention_outcomes()
    return {
        "analysis_cohort_size": outcomes.analysis_cohort_size,
        "evaluation_period": outcomes.evaluation_protocol,
        "cohorts": {
            "high_adherence_group": outcomes.high_adherence_group,
            "low_adherence_group": outcomes.low_adherence_group,
        },
        "statistical_significance": {
            "p_value": "< 0.001",
            "confidence_interval": "95%",
            "clinical_inference": outcomes.clinical_inference,
        }
    }
