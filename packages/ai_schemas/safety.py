"""Clinical AI Safety & Governance Schemas for SevaHealth AI.

Defines schemas for:
- Clinical safety envelopes (source data, timestamp, version, confidence, limitations, human verification state)
- Mandatory safety banners
- Emergency routing payloads
- Safety violations and audit events

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HumanVerificationState(str, Enum):
    """Human-in-the-loop verification states for AI-generated clinical outputs."""
    PENDING_REVIEW = "PENDING_REVIEW"
    CLINICIAN_VERIFIED = "CLINICIAN_VERIFIED"
    CLINICIAN_MODIFIED = "CLINICIAN_MODIFIED"
    REJECTED = "REJECTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SafetyBanner(str, Enum):
    """Mandatory standardized clinical safety banners."""
    RISK_ASSESSMENT = "This is a risk assessment, not a diagnosis."
    PROFESSIONAL_REVIEW = "AI-generated information must be reviewed by a healthcare professional."
    EMERGENCY = "Seek urgent medical care for emergency symptoms."


class EmergencyRoutingDetails(BaseModel):
    """Payload for routing urgent clinical presentations to human emergency workflows."""
    is_emergency: bool = True
    urgency_level: str = "CRITICAL_EMERGENCY"  # CRITICAL_EMERGENCY | URGENT_SAME_DAY | ROUTINE
    trigger_reasons: List[str]
    emergency_contact_numbers: List[str] = Field(default_factory=lambda: ["108 (Ambulance / Emergency)", "112 (National Emergency)"])
    recommended_action: str
    nearest_care_facility_type: str = "Primary Health Center / District Hospital Emergency Department"
    dispatched_alert_id: Optional[str] = None
    routed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ClinicalSafetyEnvelope(BaseModel):
    """Mandatory safety envelope wrapping every AI clinical and risk output.
    
    Ensures complete clinical provenance, transparency, confidence bounds,
    and human-in-the-loop governance.
    """
    source_data: Dict[str, Any] = Field(
        description="Snapshot or verified hash of observations, vitals, and lab parameters evaluated"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp of output generation"
    )
    model_version: str = Field(
        default="v1.0.0",
        description="Exact model artifact version"
    )
    agent_version: str = Field(
        default="v1.0.0",
        description="Exact agent prompt and logic version"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Calculated confidence score (0.0 - 1.0) based on biomarker completeness"
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Explicit clinical limitations, missingness caveats, or unmodeled confounders"
    )
    human_verification_state: HumanVerificationState = Field(
        default=HumanVerificationState.PENDING_REVIEW,
        description="Current state in the human-in-the-loop review workflow"
    )
    safety_banners: List[str] = Field(
        default_factory=lambda: [
            SafetyBanner.RISK_ASSESSMENT.value,
            SafetyBanner.PROFESSIONAL_REVIEW.value,
        ],
        description="Standardized user-facing safety banners"
    )
    emergency_routing_triggered: bool = Field(
        default=False,
        description="True if critical symptoms or vitals forced immediate emergency escalation"
    )
    emergency_routing: Optional[EmergencyRoutingDetails] = None
    safety_violations_detected: List[str] = Field(
        default_factory=list,
        description="Audit log of blocked prohibited terms or hallucination mitigations"
    )
    reviewing_clinician_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    clinician_notes: Optional[str] = None

    def add_banner(self, banner: SafetyBanner | str) -> None:
        val = banner.value if isinstance(banner, SafetyBanner) else banner
        if val not in self.safety_banners:
            self.safety_banners.append(val)

    def trigger_emergency(self, reasons: List[str], recommended_action: str) -> None:
        self.emergency_routing_triggered = True
        self.add_banner(SafetyBanner.EMERGENCY)
        self.emergency_routing = EmergencyRoutingDetails(
            is_emergency=True,
            urgency_level="CRITICAL_EMERGENCY",
            trigger_reasons=reasons,
            recommended_action=recommended_action,
        )
