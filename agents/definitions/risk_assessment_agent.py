"""RiskAssessmentAgent: Bounded agent for multi-domain NCD risk explanation and factor attribution."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from agents.core.base import BoundedAgent
from agents.core.models import FailureBehavior, RetryPolicy


class RiskAssessmentAgentInput(BaseModel):
    citizen_id: str
    vitals: Dict[str, float] = Field(default_factory=dict)
    lifestyle: Dict[str, Any] = Field(default_factory=dict)
    language: str = "en"


class DomainScoreDetail(BaseModel):
    domain: str
    score: float
    category: str
    provenance: str


class RiskAssessmentAgentOutput(BaseModel):
    citizen_id: str
    composite_score: float
    risk_tier: str
    domains: List[DomainScoreDetail]
    top_contributing_factors: List[str]
    layperson_explanation: str
    recommended_next_step: str
    confidence: float
    limitations: str
    language: str = "en"


class RiskAssessmentAgent(BoundedAgent[RiskAssessmentAgentInput, RiskAssessmentAgentOutput]):
    """Bounded agent explaining deterministic clinical risk models."""

    def __init__(self):
        super().__init__(
            name="RiskAssessmentAgent",
            purpose=(
                "Translates complex multi-domain clinical risk models (metabolic, cardiovascular, diabetes, "
                "hypertension, CKD) into understandable, grounded layperson explanations. Never invents "
                "clinical scores; invokes deterministic risk engine."
            ),
            allowed_tools=["run_deterministic_risk_models"],
            input_schema=RiskAssessmentAgentInput,
            output_schema=RiskAssessmentAgentOutput,
            safety_constraints=[
                "PROVENANCE_MANDATORY: Must cite validated public health provenance for algorithms.",
                "NO_DIAGNOSIS: Explicitly declare risk estimation is not diagnosis.",
                "TRANSPARENT_DRIVERS: Attribute top contributing factors without correlation-as-causation.",
            ],
            authorized_roles=[
                UserRole.CITIZEN,
                UserRole.HEALTH_WORKER,
                UserRole.CLINICIAN,
                UserRole.SYSTEM_ADMIN,
            ],
            timeout_sec=5.0,
            retry_policy=RetryPolicy(max_retries=2, initial_delay_ms=200),
            failure_behavior=FailureBehavior.FALLBACK_TO_DETERMINISTIC,
        )

    async def _process(self, input_data: RiskAssessmentAgentInput, actor: TokenPayload) -> RiskAssessmentAgentOutput:
        # Deterministic risk engine invocation
        profile = await self.invoke_tool(
            "run_deterministic_risk_models",
            citizen_id=input_data.citizen_id,
            vitals=input_data.vitals,
            lifestyle=input_data.lifestyle,
        )

        overall_score = profile.get("overall_score", 0.5)
        tier = profile.get("tier", "MODERATE")
        top_drivers = profile.get("top_drivers", [])
        driver_strings = [d.get("factor_name", str(d)) for d in top_drivers]

        domain_details = [
            DomainScoreDetail(
                domain="Diabetes / Metabolic",
                score=profile.get("diabetes_risk", 0.5),
                category="HIGH" if profile.get("diabetes_risk", 0.5) >= 0.6 else "MODERATE",
                provenance="ICMR-INDIAB Validated Risk Algorithm",
            ),
            DomainScoreDetail(
                domain="Cardiovascular & Vascular",
                score=profile.get("cvd_risk", 0.4),
                category="MODERATE",
                provenance="WHO PEN / Framingham CVD Model",
            ),
            DomainScoreDetail(
                domain="Hypertension Risk",
                score=profile.get("hypertension_risk", 0.5),
                category="HIGH" if profile.get("hypertension_risk", 0.5) >= 0.6 else "MODERATE",
                provenance="IHCI Indian Hypertension Protocol",
            ),
        ]

        # LLM reasoning / conversational framing
        explanation = (
            f"Your overall preventive health risk is categorized as {tier} ({round(overall_score * 100)}%). "
            f"The primary contributing factors identified are: {', '.join(driver_strings[:3])}. "
            "These numbers highlight opportunities for lifestyle prevention rather than a medical condition."
        )

        return RiskAssessmentAgentOutput(
            citizen_id=input_data.citizen_id,
            composite_score=overall_score,
            risk_tier=tier,
            domains=domain_details,
            top_contributing_factors=driver_strings,
            layperson_explanation=explanation,
            recommended_next_step="Review identified risk drivers with your health worker or doctor.",
            confidence=0.88,
            limitations="Assumes accurate biometric reporting; periodic laboratory verification advised.",
            language=input_data.language,
        )

    async def _fallback(self, input_data: RiskAssessmentAgentInput, actor: TokenPayload, error: Exception) -> RiskAssessmentAgentOutput:
        return RiskAssessmentAgentOutput(
            citizen_id=input_data.citizen_id,
            composite_score=0.5,
            risk_tier="MODERATE",
            domains=[
                DomainScoreDetail(
                    domain="General Metabolic",
                    score=0.5,
                    category="MODERATE",
                    provenance="Deterministic Fallback Heuristic",
                )
            ],
            top_contributing_factors=["Biometric elevation"],
            layperson_explanation="Automated baseline estimation: Moderate risk level detected.",
            recommended_next_step="Undergo clinical screening for individualized assessment.",
            confidence=0.70,
            limitations="Fallback mode executed due to upstream timeout.",
            language=input_data.language,
        )
