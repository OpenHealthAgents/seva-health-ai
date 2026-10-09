"""FastAPI Router for SevaHealth Population Health Intelligence.

Provides population-level aggregated epidemiological analytics, risk distributions,
longitudinal trends, intervention outcomes, and referral pipeline metrics with strict
k-anonymity (k >= 10) cell suppression and salted pseudonymized data export.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from packages.auth.jwt import get_current_user_token, TokenPayload, require_roles
from packages.types.enums import UserRole
from services.population_intelligence.analytics import (
    get_population_overview,
    get_risk_distribution,
    get_risk_trends,
    get_high_risk_cohorts,
    get_intervention_outcomes,
    get_referral_pipeline,
    get_community_comparison,
    get_deidentified_export,
    get_regional_epidemiological_metrics,
    calculate_intervention_outcome_delta,
)
from services.population_intelligence.models import (
    PopulationOverviewResponse,
    RiskDistributionResponse,
    RiskTrendsResponse,
    HighRiskCohortsResponse,
    InterventionOutcomesResponse,
    ReferralPipelineResponse,
    CommunityComparisonResponse,
    DeidentifiedExportResponse,
)

router = APIRouter(prefix="/population", tags=["Population Health Intelligence"])


@router.get(
    "/overview",
    response_model=PopulationOverviewResponse,
    summary="Get Population Overview & Primary Health KPIs",
)
async def get_overview(
    district: Optional[str] = Query(None, description="Filter by district (e.g., 'Mysuru')"),
    program: Optional[str] = Query(None, description="Filter by public health program"),
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Returns state/district-level population screening coverage, high-risk percentages,

    disease prevalence, follow-up, adherence, and referral KPIs with k-anonymity protection.
    """
    return get_population_overview(district=district, program=program)


@router.get(
    "/risk-distribution",
    response_model=RiskDistributionResponse,
    summary="Get Multi-Domain NCD Risk Distributions",
)
async def get_risk_dist(
    district: Optional[str] = Query("All", description="Filter by district"),
    program: Optional[str] = Query("All", description="Filter by program"),
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Returns prevalence rates and stratification across Low, Moderate, High, Critical

    tiers for Diabetes, Hypertension, CVD, Central Obesity, and Renal Health.
    """
    return get_risk_distribution(district=district, program=program)


@router.get(
    "/risk-trends",
    response_model=RiskTrendsResponse,
    summary="Get Longitudinal Multi-Month Risk Trajectories",
)
async def get_trends(
    district: Optional[str] = Query("All", description="Filter by district"),
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Returns 6-month longitudinal trends in screening volume, high-risk detection,

    care plan adoption, adherence, and risk tier downgrades.
    """
    return get_risk_trends()


@router.get(
    "/high-risk-cohorts",
    response_model=HighRiskCohortsResponse,
    summary="Get Stratified High-Risk Sub-Populations with Privacy Suppression",
)
async def get_cohorts(
    district: Optional[str] = Query("All", description="Filter by district"),
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Identifies prioritized high-risk cohorts with clinical biomarker drivers and

    recommended public health outreach. Suppresses any cohort cell with count < 10.
    """
    return get_high_risk_cohorts()



@router.get(
    "/intervention-outcomes",
    response_model=InterventionOutcomesResponse,
    summary="Get Evidence-Based Prevention Program Outcomes",
)
async def get_outcomes(
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Evaluates 90-day clinical delta comparing high-adherence vs low-adherence

    prevention cohort participants (Systolic BP, Fasting Glucose, Risk Downgrades).
    """
    return get_intervention_outcomes()


@router.get(
    "/referral-pipeline",
    response_model=ReferralPipelineResponse,
    summary="Get Closed-Loop Referral Pipeline & Bottleneck Analysis",
)
async def get_pipeline(
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Tracks public health referral progression from ASHA identification through PHC/CHC

    consultation, specialist review, and confirmed treatment initiation.
    """
    return get_referral_pipeline()


@router.get(
    "/community-comparison",
    response_model=CommunityComparisonResponse,
    summary="Get Cross-District & Community Performance Benchmarks",
)
async def get_communities(
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Ranks districts and communities on the Ayushman Bharat Performance Index

    (Screening Coverage, Adherence, Referral Completion).
    """
    return get_community_comparison()


@router.get(
    "/deidentified-export",
    response_model=DeidentifiedExportResponse,
    summary="Export De-Identified Public Health Research Microdata",
)
async def get_export(
    limit: int = Query(50, ge=1, le=500, description="Number of sample records"),
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Produces de-identified research microdata with salted SHA-256 pseudonyms,

    5-year age bands, and categorized clinical indicators. Zero individual PII exposed.
    """
    return get_deidentified_export(limit=limit)


@router.post(
    "/export-async",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asynchronously Generate & Export Population Microdata",
)
async def export_population_microdata_async(
    limit: int = Query(500, ge=1, le=50000, description="Cohort size to export"),
    district: Optional[str] = Query("All", description="District filter"),
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Enqueues heavy district-level aggregation and k-anonymity pseudonymization to background queue."""
    from packages.queue.manager import job_queue_manager
    from packages.queue.models import QueueType, JobPriority

    job = await job_queue_manager.enqueue(
        queue=QueueType.POPULATION_ANALYTICS,
        payload={"cohort_size": limit, "district": district},
        priority=JobPriority.NORMAL,
        tenant_id=current_user.tenant_id,
    )
    return {
        "status": "QUEUED",
        "job_id": job.id,
        "district": district,
        "sample_size": limit,
        "message": "Population export processing in background.",
        "status_url": f"/api/v1/jobs/{job.id}",
    }


# ==============================================================================
# Legacy Endpoints (Maintained for Backward Compatibility)
# ==============================================================================

@router.get("/metrics", summary="Legacy Regional Epidemiological Metrics")
async def get_population_metrics(
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.CLINICIAN, UserRole.SYSTEM_ADMIN])
    ),
):
    """District-level NCD prevalence heatmaps and risk distribution."""
    return get_regional_epidemiological_metrics()


@router.get("/outcome-delta", summary="Legacy Intervention Outcome Delta")
async def get_intervention_outcome_delta(
    current_user: TokenPayload = Depends(
        require_roles([UserRole.PUBLIC_HEALTH_ADMIN, UserRole.CLINICIAN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Measures clinical outcome improvement comparing high vs low adherence cohorts."""
    return calculate_intervention_outcome_delta()
