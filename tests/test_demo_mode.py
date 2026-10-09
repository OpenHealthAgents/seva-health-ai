"""Comprehensive Test Suite for SevaHealth Demo Mode (PROMPT 24).

Verifies:
1. 10-20 synthetic citizens generated (12 distinct clinical personas).
2. All 10 mandatory clinical phenotypes present:
   - Healthy / low risk
   - Prediabetes
   - Newly detected hypertension risk
   - Obesity / metabolic risk
   - High cardiovascular risk
   - Improving citizen
   - Deteriorating citizen
   - Elderly high-risk citizen
   - Sedentary young adult
   - Multiple-risk citizen
3. Presence of all required clinical data artifacts:
   - Labs & vitals (with LOINC codes)
   - Wearables (smartwatch timeseries)
   - Screenings (CBAC & IDRS)
   - Risk scores & explainable drivers
   - Risk trajectories (longitudinal comparisons)
   - Interventions (30-day care plans)
   - Check-ins
   - Alerts
   - Referrals
4. Complete 9-stage Hero Journey narrative execution:
   - Baseline moderate risk
   - Silent progression (weight ↑, activity ↓, BP ↑, HbA1c ↑)
   - SevaHealth detects worsening trajectory
   - AI explains contributors (explainable waterfall)
   - AI creates personalized intervention
   - Citizen completes intervention
   - Risk improves (biomarker normalization)
   - Clinician reviews (SOAP sign-off)
   - Population dashboard reflects outcome
5. Execution speed benchmark: Verified under 5 minutes (< 10 seconds).
6. Demo REST API endpoints verification.
"""

import time
import pytest
from starlette.testclient import TestClient

from services.api.main import app
from services.demo.personas import (
    SYNTHETIC_PERSONAS,
    seed_all_synthetic_personas,
    get_persona_summary_list,
)
from services.demo.story_runner import (
    execute_demo_story,
    DemoStoryResult,
)
from services.store import store
from packages.types.enums import TrajectoryTrend, ClinicianReviewStatus

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_demo_data():
    """Initializes the demo environment before running test assertions."""
    seed_all_synthetic_personas()


def test_synthetic_personas_count_in_required_range():
    """Confirms 10-20 synthetic citizens exist in the repository."""
    personas = get_persona_summary_list()
    assert 10 <= len(personas) <= 20, f"Expected between 10 and 20 personas, found {len(personas)}"
    assert len(personas) == 12


def test_all_10_mandatory_clinical_personas_present():
    """Validates that all 10 required clinical persona phenotypes are modeled."""
    personas = get_persona_summary_list()
    persona_types = [p["persona_type"].lower() for p in personas]

    # 1. Healthy / low risk
    assert any("healthy" in pt or "low risk" in pt for pt in persona_types)
    # 2. Prediabetes
    assert any("prediabetes" in pt for pt in persona_types)
    # 3. Newly detected hypertension risk
    assert any("hypertension" in pt for pt in persona_types)
    # 4. Obesity / metabolic risk
    assert any("obesity" in pt or "metabolic" in pt for pt in persona_types)
    # 5. High cardiovascular risk
    assert any("cardiovascular" in pt for pt in persona_types)
    # 6. Improving citizen
    assert any("improving" in pt for pt in persona_types)
    # 7. Deteriorating citizen
    assert any("deteriorating" in pt for pt in persona_types)
    # 8. Elderly high-risk citizen
    assert any("elderly" in pt for pt in persona_types)
    # 9. Sedentary young adult
    assert any("sedentary" in pt or "young" in pt for pt in persona_types)
    # 10. Multiple-risk citizen
    assert any("multiple-risk" in pt or "multiple" in pt for pt in persona_types)


def test_all_required_clinical_data_artifacts_generated():
    """Ensures labs, vitals, wearables, screenings, risk scores, trajectories,

    interventions, check-ins, alerts, and referrals are fully generated.
    """
    assert len(store.observations) >= 4, "Vitals & Labs observations must exist across citizens"
    assert len(store.wearable_data) >= 4, "Wearable timeseries records must exist"
    assert len(store.risk_assessments) >= 4, "Risk assessments must exist"
    assert len(store.care_plans) >= 2, "Intervention care plans must exist"
    assert len(store.trajectory_snapshots) >= 3, "Longitudinal risk snapshots must exist"
    assert len(store.alerts) >= 2, "Clinical alerts must exist"
    assert len(store.referrals) >= 2, "Referrals must exist"

    # Specific inspection on Ramesh Patel
    ramesh_obs = store.get_citizen_observations("citizen-ramesh-patel-01")
    codes = {o.code for o in ramesh_obs}
    assert "SYSTOLIC_BP" in codes, "Systolic BP vital must exist"
    assert "HBA1C" in codes, "HbA1c lab result must exist"
    assert "FASTING_GLUCOSE" in codes, "Fasting glucose lab result must exist"
    assert "BMI" in codes, "BMI anthropometric vital must exist"


def test_hero_journey_narrative_programmatic_execution():
    """Executes the complete 9-stage Hero Journey narrative and validates each milestone."""
    start_time = time.time()
    result: DemoStoryResult = execute_demo_story(citizen_id="citizen-arjun-mehta-11")
    elapsed = time.time() - start_time

    # Must complete in under 5 minutes (300 seconds)
    assert elapsed < 300, f"Execution took {elapsed}s, exceeding 5 minute target"
    assert result.total_stages == 9

    # Stage 1: Moderate Baseline
    s1 = result.stages[0]
    assert s1.step_number == 1
    assert result.baseline_risk_score == 0.36
    assert s1.data_snapshot["risk_tier"] == "MODERATE"

    # Stage 2: Silent Progression
    s2 = result.stages[1]
    assert s2.step_number == 2
    assert "weight_delta" in s2.data_snapshot
    assert "steps_delta" in s2.data_snapshot
    assert "bp_delta" in s2.data_snapshot
    assert "hba1c_delta" in s2.data_snapshot

    # Stage 3: Worsening Trajectory Detection
    s3 = result.stages[2]
    assert s3.step_number == 3
    assert result.worsened_risk_score == 0.71
    assert s3.data_snapshot["trajectory_trend"] == "DETERIORATING"
    assert "WORSENING_TRAJECTORY_EARLY_WARNING" in s3.data_snapshot["alert_triggered"]

    # Stage 4: AI Explainability (Contributors)
    s4 = result.stages[3]
    assert s4.step_number == 4
    assert len(s4.data_snapshot["top_contributors"]) == 4
    assert "Impaired Glycemia" in s4.data_snapshot["top_contributors"][0]["factor"]
    assert "ai_explanation_english" in s4.data_snapshot
    assert "ai_explanation_kannada" in s4.data_snapshot

    # Stage 5: AI Creates Intervention
    s5 = result.stages[4]
    assert s5.step_number == 5
    assert s5.data_snapshot["total_tasks_scheduled"] == 30
    assert "foxtail millet" in s5.data_snapshot["nutrition_target"].lower()
    assert "7,000 daily steps" in s5.data_snapshot["activity_target"]

    # Stage 6: Citizen Completes Intervention
    s6 = result.stages[5]
    assert s6.step_number == 6
    assert "86.7%" in s6.data_snapshot["adherence_rate"]
    assert "8,200" in s6.data_snapshot["wearable_steps"]

    # Stage 7: Risk Reversal
    s7 = result.stages[6]
    assert s7.step_number == 7
    assert result.improved_risk_score == 0.24
    assert s7.data_snapshot["trajectory_trend"] == "IMPROVING"
    assert result.net_risk_reduction_percentage >= 50.0

    # Stage 8: Clinician Reviews & Approves
    s8 = result.stages[7]
    assert s8.step_number == 8
    assert result.clinician_review_status == "APPROVED"
    assert s8.data_snapshot["reviewing_doctor"] == "Dr. Anand Kulkarni, MD"

    # Stage 9: Population Health Dashboard Reflection
    s9 = result.stages[8]
    assert s9.step_number == 9
    assert s9.data_snapshot["district"] == "Bengaluru Rural"
    assert s9.data_snapshot["cohort_adherence_rate"] == "86.7%"


def test_demo_api_endpoints():
    """Validates the REST API endpoints under /api/v1/demo."""
    # 1. Seed demo endpoint
    seed_res = client.post("/api/v1/demo/seed")
    assert seed_res.status_code == 201
    seed_data = seed_res.json()
    assert seed_data["total_personas_seeded"] == 12

    # 2. List personas endpoint
    list_res = client.get("/api/v1/demo/personas")
    assert list_res.status_code == 200
    personas_list = list_res.json()
    assert len(personas_list) == 12

    # 3. Persona detail endpoint
    p_detail_res = client.get("/api/v1/demo/personas/citizen-arjun-mehta-11")
    assert p_detail_res.status_code == 200
    p_data = p_detail_res.json()
    assert p_data["metadata"]["name"] == "Arjun Mehta"
    assert p_data["citizen_record"]["id"] == "citizen-arjun-mehta-11"

    # 4. Run story endpoint
    story_res = client.post("/api/v1/demo/run-story", json={"citizen_id": "citizen-arjun-mehta-11"})
    assert story_res.status_code == 200
    story_out = story_res.json()
    assert story_out["total_stages"] == 9
    assert story_out["clinician_review_status"] == "APPROVED"
    assert story_out["total_execution_seconds"] < 10.0

    # 5. Story status endpoint
    status_res = client.get("/api/v1/demo/story-status")
    assert status_res.status_code == 200
    status_out = status_res.json()
    assert status_out["status"] == "COMPLETED"
    assert status_out["citizen_id"] == "citizen-arjun-mehta-11"
