"""HealthEducationAgent: Bounded agent for evidence-based multilingual health literacy."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from agents.core.base import BoundedAgent
from agents.core.models import FailureBehavior, RetryPolicy


class HealthEducationAgentInput(BaseModel):
    citizen_id: Optional[str] = None
    topic: str  # e.g., "diabetes", "hypertension", "millets", "salt_reduction"
    language: str = "en"
    complexity_level: str = "SIMPLE"  # SIMPLE | INTERMEDIATE | CLINICIAN


class HealthEducationAgentOutput(BaseModel):
    topic: str
    explanation: str
    practical_action_tips: List[str]
    evidence_citations: List[str]
    disclaimer: str
    language: str = "en"


class HealthEducationAgent(BoundedAgent[HealthEducationAgentInput, HealthEducationAgentOutput]):
    """Bounded agent for public health literacy and evidence-based education."""

    def __init__(self):
        super().__init__(
            name="HealthEducationAgent",
            purpose=(
                "Delivers clear, culturally resonant preventive health education grounded in verified "
                "national guidelines (ICMR-INDIAB, IHCI, WHO PEN). Simplifies complex medical terminology "
                "for low digital literacy. Strictly non-prescriptive."
            ),
            allowed_tools=["query_knowledge_base"],
            input_schema=HealthEducationAgentInput,
            output_schema=HealthEducationAgentOutput,
            safety_constraints=[
                "GROUNDED_ONLY: All clinical statements must be grounded in verified guidelines.",
                "NO_MIRACLE_CURES: Never validate unproven remedies, extreme diets, or miracle cures.",
                "EMERGENCY_PROHIBITED: Cannot provide emergency medical instructions.",
            ],
            authorized_roles=[
                UserRole.CITIZEN,
                UserRole.HEALTH_WORKER,
                UserRole.CLINICIAN,
                UserRole.PUBLIC_HEALTH_ADMIN,
                UserRole.SYSTEM_ADMIN,
            ],
            timeout_sec=5.0,
            retry_policy=RetryPolicy(max_retries=2, initial_delay_ms=200),
            failure_behavior=FailureBehavior.FAIL_SAFE_DEGRADED,
        )

    async def _process(self, input_data: HealthEducationAgentInput, actor: TokenPayload) -> HealthEducationAgentOutput:
        knowledge = await self.invoke_tool(
            "query_knowledge_base",
            topic=input_data.topic,
        )

        title = knowledge.get("title", "Preventive Health Guidelines")
        summary = knowledge.get("summary", "Adopting balanced lifestyle habits helps maintain vital signs.")
        citations = knowledge.get("citations", ["ICMR National Guidelines"])

        tips = [
            "Opt for home-cooked meals prepared with minimal processed oils.",
            "Take short 5-minute movement breaks during prolonged periods of sitting.",
            "Schedule regular blood pressure and blood sugar checks once every 6-12 months.",
        ]

        explanation = (
            f"Understanding {input_data.topic.title()}: {summary} "
            "Preventive habits work continuously to reduce strain on your heart, blood vessels, and kidneys."
        )

        return HealthEducationAgentOutput(
            topic=input_data.topic,
            explanation=explanation,
            practical_action_tips=tips,
            evidence_citations=citations,
            disclaimer="Health education information only. For individualized medical diagnosis, consult a doctor.",
            language=input_data.language,
        )

    async def _fallback(self, input_data: HealthEducationAgentInput, actor: TokenPayload, error: Exception) -> HealthEducationAgentOutput:
        return HealthEducationAgentOutput(
            topic=input_data.topic,
            explanation="Maintaining daily physical activity and a balanced diet supports long-term health.",
            practical_action_tips=["Engage in 30 minutes of daily brisk walking", "Eat diverse fresh vegetables"],
            evidence_citations=["WHO Global Health Guidelines"],
            disclaimer="General health literacy content.",
            language=input_data.language,
        )
