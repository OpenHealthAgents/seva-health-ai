"""Comprehensive Test Suite for Seva Innovation Challenge Demo Workflow (PROMPT 25).

Verifies:
1. All 16 challenge steps execute in exact sequence with correct clinical actors:
   - STEP 1: Health worker registers citizen.
   - STEP 2: Citizen completes NCD screening.
   - STEP 3: System calculates risk.
   - STEP 4: AI explains risk.
   - STEP 5: System generates personalized prevention plan.
   - STEP 6: Citizen connects wearable.
   - STEP 7: System receives activity/sleep/heart-rate data.
   - STEP 8: Risk trajectory changes.
   - STEP 9: AI detects deterioration.
   - STEP 10: High-risk alert is generated.
   - STEP 11: Clinician reviews the patient.
   - STEP 12: Clinician creates/approves care plan.
   - STEP 13: Citizen receives intervention.
   - STEP 14: Follow-up measurement is recorded.
   - STEP 15: Risk trajectory improves.
   - STEP 16: Population dashboard shows aggregate impact.
2. The "Demo Reset Button" restores pristine initial state.
3. Execution performance benchmark: Completes in under 5 minutes (< 10 seconds).
4. REST API endpoints for full run, step-by-step, reset, and state retrieval.
"""

import time
import pytest
from starlette.testclient import TestClient

from services.api.main import app
from services.store import store
from services.demo.challenge_workflow import (
    execute_challenge_step,
    execute_all_challenge_steps,
    reset_challenge_demo,
    get_challenge_demo_state,
    CHALLENGE_CITIZEN_ID,
    ChallengeStepRecord,
    ChallengeWorkflowSummary,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_demo():
    """Ensure clean challenge environment before each test."""
    reset_challenge_demo()
    yield
    reset_challenge_demo()


def test_all_16_challenge_steps_sequential_execution():
    """Validates that each of the 16 steps can be stepped through sequentially."""
    for s in range(1, 17):
        rec = execute_challenge_step(s)
        assert rec.step_number == s
        assert rec.status == "COMPLETED"
        assert rec.execution_time_ms >= 0

    # Step 1: Health worker registration
    s1 = execute_challenge_step(1)
    assert s1.actor_role == "HEALTH_WORKER"
    assert s1.telemetry["citizen_id"] == CHALLENGE_CITIZEN_ID
    assert s1.telemetry["abha_id"] == "91-7291-3849-1029"

    # Step 2: NCD Screening
    s2 = execute_challenge_step(2)
    assert s2.actor_role == "CITIZEN"
    assert s2.telemetry["cbac_score"] == 5
    assert s2.telemetry["idrs_score"] == 60

    # Step 3: Risk Calculation
    s3 = execute_challenge_step(3)
    assert s3.actor_role == "SYSTEM"
    assert s3.telemetry["overall_composite_score"] == 0.52
    assert s3.telemetry["overall_risk_tier"] == "MODERATE"

    # Step 4: AI Explainability
    s4 = execute_challenge_step(4)
    assert s4.actor_role == "AI_ENGINE"
    assert len(s4.telemetry["attribution_waterfall"]) == 5
    assert "en" in s4.telemetry["multilingual_explanations"]
    assert "kn" in s4.telemetry["multilingual_explanations"]

    # Step 5: Prevention Plan
    s5 = execute_challenge_step(5)
    assert s5.actor_role == "SYSTEM"
    assert s5.telemetry["duration_days"] == 30
    assert s5.telemetry["total_scheduled_tasks"] == 30

    # Step 6: Wearable Pairing
    s6 = execute_challenge_step(6)
    assert s6.actor_role == "CITIZEN"
    assert s6.telemetry["device_pairing"]["connection_status"] == "CONNECTED"

    # Step 7: Telemetry Ingestion
    s7 = execute_challenge_step(7)
    assert s7.actor_role == "SYSTEM"
    assert s7.telemetry["days_synced"] == 14

    # Step 8: Risk Trajectory Change
    s8 = execute_challenge_step(8)
    assert s8.actor_role == "SYSTEM"
    assert s8.telemetry["snapshots_recorded"] >= 2

    # Step 9: AI Deterioration Detection
    s9 = execute_challenge_step(9)
    assert s9.actor_role == "AI_ENGINE"
    assert s9.telemetry["trajectory_trend"] == "DETERIORATING"
    assert s9.telemetry["velocity_classification"] == "ACCELERATED_DETERIORATION"

    # Step 10: High-Risk Alert
    s10 = execute_challenge_step(10)
    assert s10.actor_role == "SYSTEM"
    assert s10.telemetry["urgency"] == "PRIORITY"

    # Step 11: Clinician Review
    s11 = execute_challenge_step(11)
    assert s11.actor_role == "CLINICIAN"
    assert s11.telemetry["is_committed_to_legal_record"] is False

    # Step 12: Clinician Approval
    s12 = execute_challenge_step(12)
    assert s12.actor_role == "CLINICIAN"
    assert s12.telemetry["legal_record_committed"] is True
    assert s12.telemetry["status"] == "APPROVED"

    # Step 13: Citizen Intervention Adherence
    s13 = execute_challenge_step(13)
    assert s13.actor_role == "CITIZEN"
    assert s13.telemetry["adherence_rate"] == "90.0%"

    # Step 14: Follow-up Measurement
    s14 = execute_challenge_step(14)
    assert s14.actor_role == "HEALTH_WORKER"
    assert s14.telemetry["clinical_status"] == "OBJECTIVE_BIOMETRIC_NORMALIZATION_CONFIRMED"

    # Step 15: Trajectory Improvement
    s15 = execute_challenge_step(15)
    assert s15.actor_role == "SYSTEM"
    assert s15.telemetry["trajectory_trend"] == "IMPROVING"
    assert "72.2%" in s15.telemetry["net_relative_risk_reduction"]

    # Step 16: Population Impact
    s16 = execute_challenge_step(16)
    assert s16.actor_role == "PUBLIC_HEALTH_ADMIN"
    assert s16.telemetry["population_command_center"]["economic_roi"]["district_annualized_cost_savings_inr"] == 37800000


def test_challenge_demo_reset_button():
    """Tests that the Demo Reset Button restores a pristine clean state."""
    # Execute full workflow
    execute_all_challenge_steps()
    assert CHALLENGE_CITIZEN_ID in store.citizens
    assert len(store.get_citizen_observations(CHALLENGE_CITIZEN_ID)) > 0
    assert len(get_challenge_demo_state()["steps"]) == 16

    # Click Reset Button
    res = reset_challenge_demo()
    assert res["status"] == "RESET_SUCCESSFUL"
    assert res["completed_steps_count"] == 0

    # Verify everything purged
    assert CHALLENGE_CITIZEN_ID not in store.citizens
    assert len(store.get_citizen_observations(CHALLENGE_CITIZEN_ID)) == 0
    state = get_challenge_demo_state()
    assert state["completed_steps_count"] == 0
    assert state["is_completed"] is False
    assert len(state["steps"]) == 0

    # Ensure demo can run again deterministically
    s1 = execute_challenge_step(1)
    assert s1.step_number == 1
    assert CHALLENGE_CITIZEN_ID in store.citizens


def test_full_workflow_execution_speed_and_numbers():
    """Asserts that the complete 16-step flow executes in seconds and delivers expected deltas."""
    start = time.time()
    summary: ChallengeWorkflowSummary = execute_all_challenge_steps()
    duration = time.time() - start

    # Strict constraint: Must finish under 5 minutes (300 seconds)
    assert duration < 300, f"Execution took {duration}s, exceeding 5 minute target"
    assert duration < 10, f"Execution took {duration}s, expected sub-10 second speed"

    assert summary.total_steps == 16
    assert summary.is_completed is True
    assert summary.baseline_risk_score == 0.52
    assert summary.peak_deteriorated_risk_score == 0.79
    assert summary.final_reversed_risk_score == 0.22
    assert summary.net_risk_reduction_percentage == 72.2
    assert summary.population_savings_inr == 37800000.0


def test_challenge_demo_rest_api():
    """Validates the FastAPI endpoints for challenge demo execution and control."""
    # 1. Reset endpoint
    resp_reset = client.post("/api/v1/challenge-demo/reset")
    assert resp_reset.status_code == 200
    assert resp_reset.json()["status"] == "RESET_SUCCESSFUL"

    # 2. Steps metadata endpoint
    resp_steps = client.get("/api/v1/challenge-demo/steps")
    assert resp_steps.status_code == 200
    steps_meta = resp_steps.json()
    assert len(steps_meta) == 16
    assert steps_meta[0]["title"] == "Health worker registers citizen"
    assert steps_meta[15]["title"] == "Population dashboard shows aggregate impact"

    # 3. Step execution endpoint
    resp_s1 = client.post("/api/v1/challenge-demo/step/1")
    assert resp_s1.status_code == 200
    assert resp_s1.json()["step_number"] == 1
    assert resp_s1.json()["actor_role"] == "HEALTH_WORKER"

    # 4. State endpoint
    resp_state = client.get("/api/v1/challenge-demo/state")
    assert resp_state.status_code == 200
    state = resp_state.json()
    assert state["completed_steps_count"] == 1
    assert state["is_completed"] is False

    # 5. Full run endpoint
    resp_run = client.post("/api/v1/challenge-demo/run")
    assert resp_run.status_code == 200
    summary = resp_run.json()
    assert summary["is_completed"] is True
    assert summary["total_steps"] == 16
    assert summary["net_risk_reduction_percentage"] == 72.2

    # 6. Alias endpoints under /api/v1/demo/challenge/*
    resp_alias_reset = client.post("/api/v1/demo/challenge/reset")
    assert resp_alias_reset.status_code == 200
    assert resp_alias_reset.json()["status"] == "RESET_SUCCESSFUL"

    resp_alias_run = client.post("/api/v1/demo/challenge/run")
    assert resp_alias_run.status_code == 200
    assert resp_alias_run.json()["total_steps"] == 16
