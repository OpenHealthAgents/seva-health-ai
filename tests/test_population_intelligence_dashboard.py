"""Comprehensive Test Suite for SevaHealth Population Health Intelligence Dashboard.

Verifies:
1. Role-Based Access Control:
   - PUBLIC_HEALTH_ADMIN and SYSTEM_ADMIN authorized.
   - CITIZEN strictly denied (HTTP 403 Forbidden).
   - Malformed/invalid tokens rejected (HTTP 401 Unauthorized).
2. All 11 Required Public Health Metrics:
   - Population screened, Screening completion, High-risk population,
   - Diabetes risk, Hypertension risk, Cardiovascular risk, Obesity risk,
   - Follow-up completion, Intervention adherence, Referral completion,
   - Risk improvement.
3. All 7 Required Dashboard Modules:
   - Population Overview
   - Risk Distribution
   - Risk Trends (Longitudinal Multi-Month)
   - High-Risk Cohorts
   - Intervention Outcomes
   - Referral Pipeline
   - Community Comparison
4. Privacy, Aggregation & De-Identification Safeguards:
   - Enforces k-anonymity (k >= 10) cell suppression.
   - Small counts (< 10) suppressed with privacy indicator.
   - Salted SHA-256 pseudonym generation.
   - Quasi-identifier generalization (age bands, clinical categorization).
   - Microdata export contains ZERO patient PII.
5. Static Web App Serving:
   - GET /public-health-app serves dashboard HTML.
"""

import pytest
from starlette.testclient import TestClient

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload, create_access_token
from services.api.main import app
from services.population_intelligence.privacy import (
    PrivacyProtectionEngine,
    MIN_CELL_SIZE_THRESHOLD,
)
from services.population_intelligence.analytics import (
    get_population_overview,
    get_risk_distribution,
    get_risk_trends,
    get_high_risk_cohorts,
    get_intervention_outcomes,
    get_referral_pipeline,
    get_community_comparison,
    get_deidentified_export,
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

client = TestClient(app)


@pytest.fixture
def public_health_admin_actor():
    return TokenPayload(
        sub="pha-director-01",
        tenant_id="karnataka_state_health",
        role=UserRole.PUBLIC_HEALTH_ADMIN,
    )


@pytest.fixture
def system_admin_actor():
    return TokenPayload(
        sub="sys-admin-01",
        tenant_id="karnataka_state_health",
        role=UserRole.SYSTEM_ADMIN,
    )


@pytest.fixture
def citizen_actor():
    return TokenPayload(
        sub="citizen-user-01",
        tenant_id="karnataka_state_health",
        role=UserRole.CITIZEN,
    )


# ==============================================================================
# 1. PRIVACY & K-ANONYMITY TESTS
# ==============================================================================

class TestPrivacyProtectionEngine:
    """Verifies mathematical k-anonymity (k >= 10) and de-identification protections."""

    def test_cell_suppression_threshold(self):
        assert MIN_CELL_SIZE_THRESHOLD == 10

        # Cells >= 10 are safely reported
        res10 = PrivacyProtectionEngine.enforce_cell_suppression(10)
        assert res10["value"] == 10
        assert res10["is_suppressed"] is False

        res42 = PrivacyProtectionEngine.enforce_cell_suppression(42)
        assert res42["value"] == 42
        assert res42["is_suppressed"] is False

        # Cells with 1 to 9 individuals are suppressed
        res1 = PrivacyProtectionEngine.enforce_cell_suppression(1)
        assert res1["value"] is None
        assert res1["is_suppressed"] is True
        assert "< 10" in res1["display"]

        res4 = PrivacyProtectionEngine.enforce_cell_suppression(4)
        assert res4["value"] is None
        assert res4["is_suppressed"] is True

        res9 = PrivacyProtectionEngine.enforce_cell_suppression(9)
        assert res9["value"] is None
        assert res9["is_suppressed"] is True

    def test_sanitize_demographic_breakdown(self):
        raw_cohort = {
            "MALE": 450,
            "FEMALE": 480,
            "OTHER": 3,   # Should be suppressed!
            "UNKNOWN": 0, # Zero count permitted
        }
        sanitized = PrivacyProtectionEngine.sanitize_demographic_breakdown(raw_cohort)

        assert sanitized["cells"]["MALE"] == 450
        assert sanitized["cells"]["FEMALE"] == 480
        assert "< 10 (Suppressed for Privacy)" in sanitized["cells"]["OTHER"]
        assert sanitized["cells"]["UNKNOWN"] == 0
        assert sanitized["suppressed_cells_count"] == 1

    def test_salted_sha256_pseudonymization(self):
        id_1 = "citizen-ramesh-patel-01"
        id_2 = "citizen-sunita-devi-02"

        pseudo_1 = PrivacyProtectionEngine.generate_pseudonym(id_1)
        pseudo_2 = PrivacyProtectionEngine.generate_pseudonym(id_2)

        # Produces valid pseudonym starting with PSEUDO-
        assert pseudo_1.startswith("PSEUDO-")
        assert pseudo_2.startswith("PSEUDO-")
        assert len(pseudo_1) == 21
        assert len(pseudo_2) == 21
        assert pseudo_1 != pseudo_2
        # Deterministic with fixed salt
        assert pseudo_1 == PrivacyProtectionEngine.generate_pseudonym(id_1)
        # Never reveals raw identifier
        assert id_1 not in pseudo_1

    def test_quasi_identifier_generalization(self):
        # Age banding (quasi-identifier grouping)
        assert PrivacyProtectionEngine.generalize_age(23) == "18-29 yrs"
        assert PrivacyProtectionEngine.generalize_age(47) == "45-49 yrs"
        assert PrivacyProtectionEngine.generalize_age(82) == "65+ yrs"

        # Blood pressure categorization
        assert "Normal" in PrivacyProtectionEngine.generalize_blood_pressure(115, 75)
        assert "Stage 1 HTN" in PrivacyProtectionEngine.generalize_blood_pressure(132, 84)
        assert "Stage 2 HTN" in PrivacyProtectionEngine.generalize_blood_pressure(155, 95)

        # Glucose categorization
        assert "Normal" in PrivacyProtectionEngine.generalize_glucose(92)
        assert "Impaired" in PrivacyProtectionEngine.generalize_glucose(112)
        assert "Elevated" in PrivacyProtectionEngine.generalize_glucose(148)


# ==============================================================================
# 2. ANALYTICS ENGINE TESTS (ALL 7 VIEWS & METRICS)
# ==============================================================================

class TestPopulationAnalyticsEngine:
    """Verifies analytics models for all 7 dashboard modules and all 11 required metrics."""

    def test_population_overview_metrics(self):
        overview = get_population_overview()
        assert isinstance(overview, PopulationOverviewResponse)

        # 11 Core Metrics Verification
        assert overview.population_screened > 10000
        assert overview.screening_completion_rate_pct > 0.0
        assert overview.high_risk_population > 2000
        assert overview.diabetes_risk_prevalence_pct > 20.0
        assert overview.hypertension_risk_prevalence_pct > 25.0
        assert overview.cardiovascular_risk_prevalence_pct > 10.0
        assert overview.obesity_risk_prevalence_pct > 15.0
        assert overview.followup_completion_rate_pct > 70.0
        assert overview.intervention_adherence_mean_pct > 70.0
        assert overview.referral_completion_rate_pct > 65.0
        assert overview.risk_improvement_count > 0

        # Privacy notice included
        assert "k >= 10" in overview.privacy_notice

        # Small demographic cohort suppression test
        demo_sex = overview.demographic_summary["sex"]
        assert "Suppressed" in str(demo_sex["OTHER"])
        assert overview.demographic_summary["suppressed_cells_count"] >= 1

    def test_population_overview_district_filter(self):
        mysuru = get_population_overview(district="Mysuru")
        assert mysuru.selected_district == "Mysuru"
        assert mysuru.total_target_population == 25000
        assert mysuru.population_screened == 3840

    def test_risk_distribution(self):
        risk_dist = get_risk_distribution()
        assert isinstance(risk_dist, RiskDistributionResponse)
        assert len(risk_dist.domains) == 5

        domain_names = [d.domain_name for d in risk_dist.domains]
        assert any("Diabetes" in name for name in domain_names)
        assert any("Hypertension" in name for name in domain_names)
        assert any("Cardiovascular" in name for name in domain_names)
        assert any("Central Obesity" in name for name in domain_names)
        assert any("Renal Health" in name for name in domain_names)

        for d in risk_dist.domains:
            assert d.low_count + d.moderate_count + d.high_count + d.critical_count > 0
            assert d.leading_risk_driver != ""

    def test_risk_trends(self):
        trends = get_risk_trends()
        assert isinstance(trends, RiskTrendsResponse)
        assert len(trends.monthly_trends) == 6

        # Check monotonic progression of screening
        screened_sequence = [m.screened_cumulative for m in trends.monthly_trends]
        assert screened_sequence == sorted(screened_sequence)
        assert len(trends.key_findings) > 0

    def test_high_risk_cohorts(self):
        cohorts = get_high_risk_cohorts()
        assert isinstance(cohorts, HighRiskCohortsResponse)
        assert len(cohorts.cohorts) >= 4

        for c in cohorts.cohorts:
            assert c.size >= cohorts.k_anonymity_threshold  # Strict k-anonymity check
            assert len(c.leading_biomarkers) > 0
            assert len(c.top_lifestyle_contributors) > 0
            assert c.suggested_public_health_intervention != ""

    def test_intervention_outcomes(self):
        outcomes = get_intervention_outcomes()
        assert isinstance(outcomes, InterventionOutcomesResponse)
        assert outcomes.analysis_cohort_size == 2400

        # Clinically significant reduction in high adherence group
        assert outcomes.mean_systolic_bp_reduction_mmhg == -6.4
        assert outcomes.mean_fasting_glucose_reduction_mgdl == -14.2
        assert outcomes.total_risk_tier_downgrades == 512
        assert "< 0.001" in outcomes.p_value

    def test_referral_pipeline(self):
        pipeline = get_referral_pipeline()
        assert isinstance(pipeline, ReferralPipelineResponse)
        assert len(pipeline.funnel_stages) == 5
        assert len(pipeline.facility_breakdown) >= 3
        assert len(pipeline.pipeline_bottlenecks) >= 2

        # Check funnel monotonic decrease in absolute counts
        counts = [stage.count for stage in pipeline.funnel_stages]
        assert counts[0] > counts[1] > counts[2] > counts[3] > counts[4]

    def test_community_comparison(self):
        comp = get_community_comparison()
        assert isinstance(comp, CommunityComparisonResponse)
        assert len(comp.communities) == 5

        district_names = [c.community_name for c in comp.communities]
        assert any("Mysuru" in name for name in district_names)
        assert any("Bengaluru Rural" in name for name in district_names)
        assert any("Mandya" in name for name in district_names)

        tiers = {c.performance_tier for c in comp.communities}
        assert "HIGH_PERFORMING" in tiers
        assert "PRIORITY_NEEDS_FOCUS" in tiers

    def test_deidentified_export(self):
        export = get_deidentified_export(limit=25)
        assert isinstance(export, DeidentifiedExportResponse)
        assert export.sample_size == 25
        assert len(export.records) == 25

        for rec in export.records:
            # 21-char pseudonym
            assert rec.pseudonym_id.startswith("PSEUDO-")
            assert len(rec.pseudonym_id) == 21
            # Generalized age band
            assert "yrs" in rec.age_group or "+" in rec.age_group
            # Zero individual real names or contact details
            assert not hasattr(rec, "name")
            assert not hasattr(rec, "phone")
            assert not hasattr(rec, "aadhaar")


# ==============================================================================
# 3. REST API ENDPOINTS & ROLE AUTHORIZATION TESTS
# ==============================================================================

class TestPopulationIntelligenceEndpoints:
    """Verifies all REST API routes and RBAC protection."""

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/population/overview",
        "/api/v1/population/risk-distribution",
        "/api/v1/population/risk-trends",
        "/api/v1/population/high-risk-cohorts",
        "/api/v1/population/intervention-outcomes",
        "/api/v1/population/referral-pipeline",
        "/api/v1/population/community-comparison",
        "/api/v1/population/deidentified-export",
    ])
    def test_public_health_admin_authorized(self, endpoint, public_health_admin_actor):
        token = create_access_token(
            subject=public_health_admin_actor.sub,
            tenant_id=public_health_admin_actor.tenant_id,
            role=public_health_admin_actor.role,
        )
        resp = client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"Failed for {endpoint}: {resp.text}"

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/population/overview",
        "/api/v1/population/risk-distribution",
        "/api/v1/population/risk-trends",
        "/api/v1/population/high-risk-cohorts",
        "/api/v1/population/intervention-outcomes",
        "/api/v1/population/referral-pipeline",
        "/api/v1/population/community-comparison",
        "/api/v1/population/deidentified-export",
    ])
    def test_system_admin_authorized(self, endpoint, system_admin_actor):
        token = create_access_token(
            subject=system_admin_actor.sub,
            tenant_id=system_admin_actor.tenant_id,
            role=system_admin_actor.role,
        )
        resp = client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/population/overview",
        "/api/v1/population/risk-distribution",
        "/api/v1/population/risk-trends",
        "/api/v1/population/high-risk-cohorts",
        "/api/v1/population/intervention-outcomes",
        "/api/v1/population/referral-pipeline",
        "/api/v1/population/community-comparison",
        "/api/v1/population/deidentified-export",
    ])
    def test_citizen_forbidden(self, endpoint, citizen_actor):
        token = create_access_token(
            subject=citizen_actor.sub,
            tenant_id=citizen_actor.tenant_id,
            role=citizen_actor.role,
        )
        resp = client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_invalid_token_rejected(self):
        resp = client.get("/api/v1/population/overview", headers={"Authorization": "Bearer invalid_malformed_token"})
        assert resp.status_code == 401

    def test_serve_public_health_web_dashboard(self):
        resp = client.get("/public-health-app")
        assert resp.status_code == 200
        assert "SevaHealth Population Intelligence" in resp.text
        assert "k-Anonymity" in resp.text
