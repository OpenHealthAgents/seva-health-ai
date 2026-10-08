from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import uuid


class WearableProvider(str, Enum):
    APPLE_HEALTH = "apple_health"
    GARMIN = "garmin"
    FITBIT = "fitbit"
    GOOGLE_FIT = "google_fit"
    WHOOP = "whoop"
    OURA = "oura"
    WITHINGS = "withings"
    MOCK = "mock_provider"


class WearableMetricType(str, Enum):
    STEPS = "steps"
    ACTIVITY = "activity"
    HEART_RATE = "heart_rate"
    HRV = "hrv"
    SLEEP = "sleep"
    WEIGHT = "weight"
    CALORIES = "calories"
    WORKOUTS = "workouts"
    BLOOD_PRESSURE = "blood_pressure"
    GLUCOSE = "glucose"
    SPO2 = "spo2"
    RESPIRATORY_RATE = "respiratory_rate"


class WearableProvenance(BaseModel):
    provider: WearableProvider
    device_brand: str
    device_model: str
    hardware_version: Optional[str] = None
    firmware_version: Optional[str] = None
    app_version: Optional[str] = None
    sync_protocol: str = "OPEN_WEARABLES_CONNECTOR_V1"
    is_medical_grade: bool = False  # NEVER assumed to be medical grade


class NormalizedWearableRecord(BaseModel):
    """Unified Normalized Health Data representation from Open Wearables layer.
    
    Adheres strictly to the architectural contract:
    - source
    - provider
    - timestamp
    - metric
    - value
    - unit
    - confidence (sensor signal quality 0.0 - 1.0)
    - provenance (device and capture details)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    citizen_id: str
    source: str
    provider: WearableProvider
    timestamp: datetime
    metric: WearableMetricType
    value: float
    unit: str
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    provenance: WearableProvenance
    metadata: Dict[str, Any] = {}
    is_medical_grade: bool = False  # Explicit consumer-grade classification

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Wearable record must contain a standardized unit.")
        return v.strip()


class WearableConnectionState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    citizen_id: str
    provider: WearableProvider
    status: str = "CONNECTED"  # CONNECTED | DISCONNECTED | REVOKED | ERROR
    access_token_masked: str
    last_sync_timestamp: Optional[datetime] = None
    last_sync_cursor: Optional[str] = None
    consent_granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    consent_revoked_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WearableProjection(BaseModel):
    """Recent / Aggregated data projections used for SevaHealth analytics.
    
    Prevents unnecessary replication of raw 100Hz telemetry databases while
    providing rich physiological features to risk engines and care plans.
    """
    citizen_id: str
    window_days: int = 7
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Heart Rate & Autonomic Tone
    avg_resting_heart_rate: float
    rhr_trend_delta: float  # +bpm (deteriorating) or -bpm (improving)
    avg_hrv_rmssd: float
    hrv_suppression_flag: bool  # True if autonomic stress / sympathetic overdrive
    
    # Physical Activity
    avg_daily_steps: int
    step_target_adherence_pct: float
    avg_active_minutes_daily: float
    
    # Sleep Hygiene
    avg_sleep_duration_hours: float
    chronic_sleep_deficit: bool  # True if < 6.0 hours on rolling average
    avg_deep_sleep_pct: float
    
    # Energy Expenditure
    avg_active_calories: float
    
    # Optional Provider Supported Metrics
    avg_systolic_bp: Optional[float] = None
    avg_glucose_mg_dl: Optional[float] = None
    
    # Regulatory & Clinical Safety Disclaimer
    clinical_safety_notice: str = (
        "CONSUMER WEARABLE ADVISORY: Wearable biometrics represent physiological trend "
        "estimates from consumer sensors. They are NOT clinically equivalent to validated "
        "medical-grade diagnostic measurements."
    )


class WebhookPayload(BaseModel):
    provider: WearableProvider
    event_type: str  # e.g., "data_updated", "device_synced", "connection_revoked"
    citizen_id: str
    data_points: List[Dict[str, Any]] = []
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
