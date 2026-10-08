import pytest
from datetime import datetime, timezone
from services.wearable.models import (
    WearableProvider,
    WearableMetricType,
    WearableConnectionState,
    WearableProjection,
    WebhookPayload,
)
from services.wearable.adapter import OpenWearablesAdapter, MockWearableProvider
from services.risk_engine.evaluator import evaluate_ncd_domains
from packages.clinical_models.observations import Observation
from packages.types.enums import TrajectoryTrend, RiskTier


@pytest.fixture
def fresh_adapter():
    return OpenWearablesAdapter()


@pytest.mark.asyncio
async def test_provider_connection_and_state(fresh_adapter):
    citizen_id = "cit-test-wearable-01"
    
    # 1. Connect Garmin
    state = await fresh_adapter.connect_provider(
        citizen_id=citizen_id,
        provider=WearableProvider.GARMIN,
        auth_payload={"access_token": "secret_garmin_oauth_token_xyz987"}
    )
    
    assert state.citizen_id == citizen_id
    assert state.provider == WearableProvider.GARMIN
    assert state.status == "CONNECTED"
    assert state.access_token_masked == "secr****z987"
    assert state.consent_granted_at is not None
    assert state.consent_revoked_at is None
    assert citizen_id in fresh_adapter.connections
    assert WearableProvider.GARMIN.value in fresh_adapter.connections[citizen_id]


@pytest.mark.asyncio
async def test_batch_sync_across_11_metric_categories(fresh_adapter):
    citizen_id = "cit-test-wearable-02"
    await fresh_adapter.connect_provider(
        citizen_id=citizen_id,
        provider=WearableProvider.GARMIN,
        auth_payload={"access_token": "token123456789"}
    )
    
    records = await fresh_adapter.sync(
        citizen_id=citizen_id,
        provider=WearableProvider.GARMIN,
        physiological_trend="DEFAULT"
    )
    
    assert len(records) > 0
    
    # Verify all 11 required physiological metric categories are present
    synced_metrics = {r.metric for r in records}
    expected_metrics = {
        WearableMetricType.STEPS,
        WearableMetricType.ACTIVITY,
        WearableMetricType.HEART_RATE,
        WearableMetricType.HRV,
        WearableMetricType.SLEEP,
        WearableMetricType.WEIGHT,
        WearableMetricType.CALORIES,
        WearableMetricType.WORKOUTS,
        WearableMetricType.BLOOD_PRESSURE,
        WearableMetricType.GLUCOSE,
        WearableMetricType.SPO2,
    }
    
    for metric in expected_metrics:
        assert metric in synced_metrics, f"Metric {metric} missing from synced wearable data"

    # Verify normalization invariants
    for r in records:
        assert r.citizen_id == citizen_id
        assert r.source in ["OPEN_WEARABLES_CONNECTOR", "OPEN_WEARABLES_OPTIONAL_EXTENSION"]
        assert r.unit != ""
        assert 0.0 <= r.confidence <= 1.0
        assert r.timestamp is not None
        assert r.is_medical_grade is False  # Never assumed to be medical grade
        assert r.provenance.is_medical_grade is False

    # Verify rolling projection computed
    projection = fresh_adapter.get_projection(citizen_id)
    assert projection is not None
    assert projection.citizen_id == citizen_id
    assert projection.window_days == 7
    assert 40.0 <= projection.avg_resting_heart_rate <= 120.0
    assert 10.0 <= projection.avg_hrv_rmssd <= 150.0
    assert projection.avg_daily_steps >= 0
    assert 0.0 <= projection.avg_sleep_duration_hours <= 14.0


@pytest.mark.asyncio
async def test_incremental_sync_with_cursor(fresh_adapter):
    citizen_id = "cit-test-wearable-03"
    await fresh_adapter.connect_provider(
        citizen_id=citizen_id,
        provider=WearableProvider.APPLE_HEALTH,
        auth_payload={"access_token": "token_apple_12345"}
    )

    # Initial sync
    delta_1, cursor_1 = await fresh_adapter.incremental_sync(citizen_id=citizen_id, cursor=None)
    assert len(delta_1) > 0
    assert cursor_1 is not None

    # Delta sync with cursor
    delta_2, cursor_2 = await fresh_adapter.incremental_sync(citizen_id=citizen_id, cursor=cursor_1)
    assert cursor_2 is not None
    assert int(cursor_2) >= int(cursor_1)
    
    # Records should have accumulated in adapter
    assert len(fresh_adapter.raw_records[citizen_id]) >= len(delta_1)


@pytest.mark.asyncio
async def test_webhook_ingest_payload(fresh_adapter):
    citizen_id = "cit-test-wearable-04"
    
    payload = WebhookPayload(
        provider=WearableProvider.WHOOP,
        event_type="recovery_updated",
        citizen_id=citizen_id,
        data_points=[
            {"metric": "heart_rate", "value": 68.0, "unit": "bpm", "confidence": 0.96},
            {"metric": "hrv", "value": 58.0, "unit": "ms", "confidence": 0.94},
            {"metric": "sleep", "value": 7.8, "unit": "hours", "confidence": 0.92},
        ]
    )
    
    res = await fresh_adapter.handle_webhook(payload)
    assert res["status"] == "ACCEPTED"
    assert res["processed_points"] == 3
    assert res["provider"] == "whoop"

    # Verifies projection calculated from webhook telemetry
    projection = fresh_adapter.get_projection(citizen_id)
    assert projection is not None
    assert projection.avg_resting_heart_rate == 68.0
    assert projection.avg_hrv_rmssd == 58.0
    assert projection.avg_sleep_duration_hours == 7.8


@pytest.mark.asyncio
async def test_disconnect_consent_revocation_and_data_deletion(fresh_adapter):
    citizen_id = "cit-test-wearable-05"
    
    await fresh_adapter.connect_provider(
        citizen_id=citizen_id,
        provider=WearableProvider.OURA,
        auth_payload={"access_token": "token_oura_test"}
    )
    await fresh_adapter.sync(citizen_id=citizen_id, provider=WearableProvider.OURA)
    
    assert citizen_id in fresh_adapter.raw_records
    assert fresh_adapter.get_projection(citizen_id) is not None

    # 1. Disconnect
    disc = await fresh_adapter.disconnect_provider(citizen_id, WearableProvider.OURA)
    assert disc is True
    assert fresh_adapter.connections[citizen_id][WearableProvider.OURA.value].status == "DISCONNECTED"

    # 2. Revoke Consent
    rev = await fresh_adapter.revoke_consent(citizen_id)
    assert rev is True
    conn_state = fresh_adapter.connections[citizen_id][WearableProvider.OURA.value]
    assert conn_state.status == "REVOKED"
    assert conn_state.consent_revoked_at is not None

    # 3. Purge / Delete all data (Right to be Forgotten)
    del_res = await fresh_adapter.delete_all_wearable_data(citizen_id)
    assert del_res is True
    assert citizen_id not in fresh_adapter.raw_records
    assert fresh_adapter.get_projection(citizen_id) is None


@pytest.mark.asyncio
async def test_wearable_modulation_of_risk_trajectory(fresh_adapter):
    """Crucial Clinical Decision Intelligence Test:
    Proves that wearable telemetry modulates risk trajectories and generates
    appropriate explainable drivers/protective factors without compromising clinical safety.
    """
    citizen_id = "cit-trajectory-demo"

    # Baseline moderate clinical observations (central adiposity & cholesterol, normal glycemic/BP)
    observations = [
        Observation(citizen_id=citizen_id, tenant_id="t1", code="SYSTOLIC_BP", value=122.0, unit="mmHg", loinc_code="8480-6", display_name="Systolic BP"),
        Observation(citizen_id=citizen_id, tenant_id="t1", code="DIASTOLIC_BP", value=78.0, unit="mmHg", loinc_code="8462-4", display_name="Diastolic BP"),
        Observation(citizen_id=citizen_id, tenant_id="t1", code="FASTING_GLUCOSE", value=92.0, unit="mg/dL", loinc_code="1558-6", display_name="Fasting Glucose"),
        Observation(citizen_id=citizen_id, tenant_id="t1", code="HBA1C", value=5.3, unit="%", loinc_code="4548-4", display_name="HbA1c"),
        Observation(citizen_id=citizen_id, tenant_id="t1", code="BMI", value=26.5, unit="kg/m2", loinc_code="39156-5", display_name="BMI"),
        Observation(citizen_id=citizen_id, tenant_id="t1", code="WAIST_CIRCUMFERENCE", value=94.0, unit="cm", loinc_code="8280-0", display_name="Waist"),
        Observation(citizen_id=citizen_id, tenant_id="t1", code="TOTAL_CHOLESTEROL", value=245.0, unit="mg/dL", loinc_code="2093-3", display_name="Cholesterol"),
        Observation(citizen_id=citizen_id, tenant_id="t1", code="TRIGLYCERIDES", value=170.0, unit="mg/dL", loinc_code="2571-8", display_name="Triglycerides"),
    ]

    # Baseline evaluation without wearable data -> Moderate risk, STABLE trajectory
    _, score_base, tier_base, traj_base, drivers_base, _ = evaluate_ncd_domains(
        observations=observations,
        idrs_score=45,
        wearable_projection=None,
    )
    assert tier_base == RiskTier.MODERATE
    assert traj_base == TrajectoryTrend.STABLE

    # --- SCENARIO A: Deteriorating Wearable Trend ---
    # Sync deteriorating wearable data (accelerating RHR, suppressed HRV, sleep loss)
    await fresh_adapter.sync(
        citizen_id=citizen_id,
        provider=WearableProvider.GARMIN,
        physiological_trend="DETERIORATING",
    )
    proj_deteriorating = fresh_adapter.get_projection(citizen_id)
    assert proj_deteriorating is not None
    assert proj_deteriorating.hrv_suppression_flag is True
    assert proj_deteriorating.rhr_trend_delta > 0

    _, _, tier_det, traj_det, drivers_det, _ = evaluate_ncd_domains(
        observations=observations,
        idrs_score=45,
        wearable_projection=proj_deteriorating,
    )
    # Trajectory must SHIFT to DETERIORATING
    assert traj_det == TrajectoryTrend.DETERIORATING
    # Must contain explainable Autonomic Strain driver
    wearable_driver = next(
        (d for d in drivers_det if "Autonomic Strain" in d.feature_name), None
    )
    assert wearable_driver is not None
    assert "HRV" in wearable_driver.observed_value
    assert wearable_driver.impact_weight > 0
    assert "Consumer-grade signal" in wearable_driver.evidence_citation

    # --- SCENARIO B: Improving Wearable Trend ---
    # Sync improving wearable data (high steps, resting bradycardia drift, robust HRV)
    citizen_improving_id = "cit-improving-demo"
    await fresh_adapter.sync(
        citizen_improving_id,
        provider=WearableProvider.GARMIN,
        physiological_trend="IMPROVING",
    )
    proj_improving = fresh_adapter.get_projection(citizen_improving_id)
    assert proj_improving is not None
    assert proj_improving.hrv_suppression_flag is False
    assert proj_improving.step_target_adherence_pct >= 85.0

    _, _, tier_imp, traj_imp, _, protective_imp = evaluate_ncd_domains(
        observations=observations,
        idrs_score=45,
        wearable_projection=proj_improving,
    )
    # Trajectory must SHIFT from STABLE to IMPROVING
    assert traj_imp == TrajectoryTrend.IMPROVING
    # Must contain Cardiorespiratory Activity protective factor
    wearable_protective = next(
        (p for p in protective_imp if "Cardiorespiratory" in p.feature_name), None
    )
    assert wearable_protective is not None
    assert "steps/day" in wearable_protective.observed_value
    assert wearable_protective.impact_weight < 0


def test_clinical_safety_notice_attached():
    """Validates that non-diagnostic consumer advisory is explicitly present."""
    proj = WearableProjection(
        citizen_id="cit-safety-check",
        avg_resting_heart_rate=72.0,
        rhr_trend_delta=0.0,
        avg_hrv_rmssd=48.0,
        hrv_suppression_flag=False,
        avg_daily_steps=8000,
        step_target_adherence_pct=100.0,
        avg_active_minutes_daily=45.0,
        avg_sleep_duration_hours=7.5,
        chronic_sleep_deficit=False,
        avg_deep_sleep_pct=22.0,
        avg_active_calories=450.0,
    )
    assert "CONSUMER WEARABLE ADVISORY" in proj.clinical_safety_notice
    assert "NOT clinically equivalent" in proj.clinical_safety_notice


@pytest.mark.asyncio
async def test_exponential_retry_handling(fresh_adapter):
    """Verifies that transient errors trigger exponential retry backoff and recover."""
    attempts = 0

    def flaky_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Transient network timeout")
        return "SUCCESS_DATA"

    result = await fresh_adapter._execute_with_retry(flaky_operation)
    assert result == "SUCCESS_DATA"
    assert attempts == 3
