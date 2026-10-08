import re
from typing import Tuple


class ClinicalSafetyEnforcer:
    """Enforces non-diagnostic clinical boundaries on all AI agent outputs (adapted from refactoragent/safety)."""

    PROHIBITED_TERMS = [
        r"\bi diagnose\b",
        r"\bi have diagnosed\b",
        r"\bmy diagnosis is\b",
        r"\bi prescribe\b",
        r"\btake this medication\b",
        r"\bstart taking metformin\b",
        r"\bstart taking amlodipine\b",
        r"\byou definitely have cancer\b",
    ]

    MANDATORY_DISCLAIMER = "Clinical review recommended. Not a medical diagnosis."

    @classmethod
    def audit_ai_response(cls, text: str) -> Tuple[bool, str]:
        """Audits AI output for safety violations."""
        for pattern in cls.PROHIBITED_TERMS:
            if re.search(pattern, text, re.IGNORECASE):
                # Sanitize out autonomous diagnosis/prescription
                sanitized = re.sub(pattern, "[CLINICAL REVIEW REQUIRED - ACTION REDACTED]", text, flags=re.IGNORECASE)
                sanitized += f"\n\nSAFETY NOTICE: {cls.MANDATORY_DISCLAIMER}"
                return False, sanitized

        if cls.MANDATORY_DISCLAIMER.lower() not in text.lower():
            text += f"\n\nSAFETY NOTICE: {cls.MANDATORY_DISCLAIMER}"

        return True, text
