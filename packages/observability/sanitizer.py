"""Healthcare Data & PHI Sanitizer for Application Logging.

Enforces strict compliance with:
"Healthcare data must NOT be written into ordinary application logs unnecessarily."

Prevents clinical biomarker values, raw vitals, patient identifiers, and diagnostic
details from leaking into stdout, console logs, or unencrypted telemetry streams.
"""

import re
from typing import Any, Dict, List, Set, Union


# Sensitive keys whose raw values must NEVER appear in ordinary application logs
SENSITIVE_CLINICAL_KEYS: Set[str] = {
    # Direct Identifiers
    "first_name",
    "last_name",
    "full_name",
    "phone",
    "phone_number",
    "email",
    "abha_id",
    "aadhaar_id",
    "address",
    "date_of_birth",
    "birth_date",
    # Hemodynamic & Biomarker Observations
    "systolic_bp",
    "diastolic_bp",
    "sbp",
    "dbp",
    "blood_pressure",
    "fasting_glucose",
    "random_glucose",
    "blood_glucose",
    "glucose",
    "hba1c",
    "serum_creatinine",
    "creatinine",
    "total_cholesterol",
    "hdl_cholesterol",
    "ldl_cholesterol",
    "triglycerides",
    "spo2",
    "oxygen_saturation",
    "heart_rate",
    "pulse",
    "body_mass_index",
    "bmi",
    "waist_circumference",
    # Clinical Diagnoses & Medications
    "medication",
    "medications",
    "prescription",
    "prescriptions",
    "dosage",
    "clinical_note",
    "clinical_summary",
    "diagnosis",
    "soap_report",
    "assessment_text",
    "observations",
    "raw_vitals",
}

# Regex patterns for accidental PHI embedded in unstructured log strings
PHONE_PATTERN = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b|(?:\+91[\-\s]?)?[6-9]\d{9}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
ABHA_PATTERN = re.compile(r"\b\d{2}-\d{4}-\d{4}-\d{4}\b")
BP_PATTERN = re.compile(r"\b\d{2,3}\s*/\s*\d{2,3}\s*mmHg\b", re.IGNORECASE)
GLUCOSE_PATTERN = re.compile(r"\b(?:glucose|sugar)\s*(?:is|=|:)?\s*\d{2,3}\s*(?:mg/dL)?\b", re.IGNORECASE)


class HealthcareLogSanitizer:
    """Sanitizes log payloads to prevent PHI and raw clinical metrics leakage."""

    REDACTED_PLACEHOLDER = "[REDACTED_CLINICAL_DATA]"
    MASKED_ID_PLACEHOLDER = "[MASKED_ID]"

    @classmethod
    def mask_citizen_id(cls, cid: str) -> str:
        """Masks citizen ID preserving prefix and suffix for tracing without exposing identity."""
        if not cid:
            return cls.MASKED_ID_PLACEHOLDER
        if len(cid) <= 8:
            return "cit-***"
        return f"{cid[:4]}...{cid[-4:]}"

    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """Scans unstructured log strings and redacts detected clinical/PII patterns."""
        if not isinstance(text, str):
            return text
        sanitized = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
        sanitized = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)
        sanitized = ABHA_PATTERN.sub("[REDACTED_ABHA]", sanitized)
        sanitized = BP_PATTERN.sub("[REDACTED_BP]", sanitized)
        sanitized = GLUCOSE_PATTERN.sub("[REDACTED_GLUCOSE]", sanitized)
        return sanitized

    @classmethod
    def sanitize_data(cls, data: Any, depth: int = 0) -> Any:
        """Recursively sanitizes dictionaries, lists, and primitives."""
        if depth > 10:  # Prevent recursion cycles
            return str(data)

        if isinstance(data, dict):
            clean: Dict[str, Any] = {}
            for k, v in data.items():
                lower_k = str(k).lower().strip()
                if lower_k in SENSITIVE_CLINICAL_KEYS:
                    clean[k] = cls.REDACTED_PLACEHOLDER
                elif lower_k in ["citizen_id", "patient_id", "subject_id", "actor_id"]:
                    clean[k] = cls.mask_citizen_id(str(v)) if isinstance(v, str) else cls.REDACTED_PLACEHOLDER
                else:
                    clean[k] = cls.sanitize_data(v, depth + 1)
            return clean

        elif isinstance(data, list):
            return [cls.sanitize_data(item, depth + 1) for item in data]

        elif isinstance(data, tuple):
            return tuple(cls.sanitize_data(item, depth + 1) for item in data)

        elif isinstance(data, str):
            return cls.sanitize_string(data)

        return data

    @classmethod
    def scrub_structlog_event(cls, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Structlog processor to ensure every logged key and event is clinical-safe."""
        sanitized = cls.sanitize_data(event_dict)
        return sanitized if isinstance(sanitized, dict) else {"event": str(sanitized)}
