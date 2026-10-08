from typing import Dict, Any, List
import json
from packages.config.settings import settings
from packages.ai_schemas.schemas import LLMRiskExplanationOutput, LLMSOAPSummaryOutput


class AIProviderInterface:
    async def explain_risk(self, citizen_name: str, vitals_summary: str, risk_score: float) -> LLMRiskExplanationOutput:
        raise NotImplementedError

    async def generate_soap_note(self, citizen_name: str, observations: Dict[str, Any], risk_tier: str) -> LLMSOAPSummaryOutput:
        raise NotImplementedError


class DeterministicMockProvider(AIProviderInterface):
    """High-fidelity, mathematically consistent mock provider for offline evaluation (adapted from refactoragent)."""

    async def explain_risk(self, citizen_name: str, vitals_summary: str, risk_score: float) -> LLMRiskExplanationOutput:
        if risk_score >= 0.70:
            summary = (
                f"{citizen_name} is currently exhibiting high physiological strain with an elevated risk trajectory. "
                "Multiple cardiovascular and metabolic parameters exceed normal preventive thresholds."
            )
            drivers = [
                "Elevated systolic vascular pressure consistently above 135 mmHg",
                "Impaired fasting blood glucose / elevated HbA1c indicative of insulin resistance",
                "Central abdominal adiposity exceeding South Asian recommended cutoffs",
            ]
            strengths = ["Sufficient baseline resting heart rate variability indicates recovery potential."]
            focus = "Reduce dietary sodium and incorporate whole ragi/millets in place of white rice."
        elif risk_score >= 0.40:
            summary = (
                f"{citizen_name} is in a moderate risk window where timely preventive lifestyle adjustments "
                "can successfully reverse early metabolic deterioration."
            )
            drivers = [
                "Sedentary lifestyle with fewer than 30 minutes of daily physical movement",
                "Mildly elevated diastolic blood pressure",
            ]
            strengths = ["Non-tobacco user with healthy kidney filtration markers."]
            focus = "Daily 15-minute post-dinner brisk walks."
        else:
            summary = f"{citizen_name} maintains a robust preventive physiological profile with low chronic disease indicators."
            drivers = ["Normal lifestyle maintenance required."]
            strengths = ["Optimal blood pressure and glycemic markers.", "Regular active daily movement."]
            focus = "Sustain current active habits and attend annual screening."

        return LLMRiskExplanationOutput(
            plain_summary=summary,
            key_drivers=drivers,
            protective_strengths=strengths,
            recommended_focus_area=focus,
        )

    async def generate_soap_note(self, citizen_name: str, observations: Dict[str, Any], risk_tier: str) -> LLMSOAPSummaryOutput:
        return LLMSOAPSummaryOutput(
            subjective=f"Patient {citizen_name} participated in community preventive health screening.",
            objective=f"Observed vitals: {json.dumps(observations)}. Evaluated Risk Tier: {risk_tier}.",
            assessment=f"Clinical decision support suggests {risk_tier} risk of lifestyle disease progression.",
            plan="1. Clinician verification of biometrics. 2. Activate 30-day preventive care plan. 3. Advise follow-up in 30 days.",
            clinical_flags=["Clinical review recommended. Not an autonomous prescription."],
        )


def get_ai_provider() -> AIProviderInterface:
    """Returns the configured AI provider, defaulting to DeterministicMockProvider for offline resilience."""
    return DeterministicMockProvider()
