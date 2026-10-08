import re
from typing import Dict, Any, Tuple


class ClinicalSanitizer:
    """Validates physiological bounds and guards against prompt injection."""

    # Physiological range sanity boundaries
    BOUNDS: Dict[str, Tuple[float, float]] = {
        "systolic_bp": (50.0, 300.0),
        "diastolic_bp": (30.0, 200.0),
        "heart_rate": (30.0, 240.0),
        "fasting_glucose": (30.0, 600.0),
        "hba1c": (3.5, 20.0),
        "total_cholesterol": (50.0, 600.0),
        "hdl_cholesterol": (10.0, 150.0),
        "triglycerides": (20.0, 1500.0),
        "bmi": (10.0, 70.0),
        "waist_circumference": (40.0, 200.0),
        "egfr": (5.0, 200.0),
    }

    # Prompt injection patterns
    INJECTION_PATTERNS = [
        r"ignore previous instructions",
        r"system prompt",
        r"you are now a doctor who diagnoses",
        r"disregard rules",
        r"forget your limitations",
        r"prescribe medicine",
    ]

    @classmethod
    def validate_vital_bounds(cls, vital_name: str, value: float) -> Tuple[bool, str]:
        if vital_name not in cls.BOUNDS:
            return True, ""
        min_v, max_v = cls.BOUNDS[vital_name]
        if not (min_v <= value <= max_v):
            return False, f"Value {value} for {vital_name} is outside valid physiological range ({min_v} - {max_v})."
        return True, ""

    @classmethod
    def sanitize_free_text(cls, text: str) -> str:
        """Sanitizes user input to prevent prompt injection and control character attacks."""
        if not text:
            return ""
        sanitized = re.sub(r"[\x00-\x1F\x7F]", " ", text)
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                sanitized = re.sub(pattern, "[BLOCKED_INSTRUCTION]", sanitized, flags=re.IGNORECASE)
        return sanitized.strip()
