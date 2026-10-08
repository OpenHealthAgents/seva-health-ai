from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import random


def generate_synthetic_wearable_timeseries(
    citizen_id: str,
    days: int = 14,
    base_rhr: float = 72.0,
    base_hrv: float = 45.0,
    base_steps: int = 6500,
    stress_trend: bool = False,
) -> List[Dict[str, Any]]:
    """Generates realistic physiological timeseries (adapted from open-wearables).

    Captures:
    - Resting Heart Rate (bpm)
    - Heart Rate Variability (HRV rMSSD in ms)
    - Total Sleep Duration (hours) & Deep Sleep percentage
    - Daily Step Count
    """
    now = datetime.now(timezone.utc)
    series: List[Dict[str, Any]] = []

    for d in range(days, 0, -1):
        record_date = (now - timedelta(days=d)).date().isoformat()
        # Introduce subtle day-to-day autonomic variance
        noise = random.uniform(-3.0, 3.0)
        drift = (days - d) * 0.4 if stress_trend else 0.0

        rhr = round(base_rhr + drift + noise, 1)
        hrv = round(max(20.0, base_hrv - (drift * 0.8) + (noise * 1.5)), 1)
        steps = int(max(1000, base_steps + random.randint(-800, 1200)))
        sleep_hrs = round(random.uniform(6.0, 8.2), 1)
        deep_sleep_pct = round(random.uniform(14.0, 24.0), 1)

        series.append({
            "citizen_id": citizen_id,
            "date": record_date,
            "resting_heart_rate": rhr,
            "hrv_rmssd": hrv,
            "daily_steps": steps,
            "sleep_duration_hours": sleep_hrs,
            "deep_sleep_percentage": deep_sleep_pct,
            "recovery_score": round(min(100.0, max(25.0, (hrv / 65.0 * 50.0) + (sleep_hrs / 8.0 * 50.0))), 1),
        })

    return series
