import pytest
from services.wearable.simulator import generate_synthetic_wearable_timeseries


def test_wearable_timeseries_generation():
    series = generate_synthetic_wearable_timeseries(
        citizen_id="c-ramesh",
        days=14,
        base_rhr=72.0,
        base_hrv=45.0,
        base_steps=6500,
    )

    assert len(series) == 14
    first_record = series[0]
    assert "resting_heart_rate" in first_record
    assert "hrv_rmssd" in first_record
    assert "daily_steps" in first_record
    assert "sleep_duration_hours" in first_record
    assert 50.0 <= first_record["resting_heart_rate"] <= 120.0
    assert 10.0 <= first_record["hrv_rmssd"] <= 150.0
