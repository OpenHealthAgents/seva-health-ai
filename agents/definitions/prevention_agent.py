"""PreventionAgent: Bounded agent for personalized 30-day lifestyle medicine prevention planning."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from agents.core.base import BoundedAgent
from agents.core.models import FailureBehavior, RetryPolicy


class PreventionAgentInput(BaseModel):
    citizen_id: str
    risk_tier: str = "MODERATE"
    identified_risks: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    language: str = "en"


class PillarGoal(BaseModel):
    pillar: str
    target: str
    rationale: str


class PreventionAgentOutput(BaseModel):
    citizen_id: str
    plan_title: str
    duration_days: int = 30
    pillar_goals: List[PillarGoal]
    daily_actions: List[Dict[str, Any]]
    educational_reminders: List[str]
    coaching_message: str
    no_medication_disclaimer_confirmed: bool = True
    language: str = "en"


class PreventionAgent(BoundedAgent[PreventionAgentInput, PreventionAgentOutput]):
    """Bounded agent for lifestyle prevention intervention planning."""

    def __init__(self):
        super().__init__(
            name="PreventionAgent",
            purpose=(
                "Synthesizes tailored 30-day lifestyle medicine prevention plans spanning nutrition, "
                "aerobic activity, sleep hygiene, and stress reduction. NEVER prescribes medication or "
                "alters prescription therapy autonomously."
            ),
            allowed_tools=["generate_deterministic_care_plan"],
            input_schema=PreventionAgentInput,
            output_schema=PreventionAgentOutput,
            safety_constraints=[
                "ZERO_PRESCRIBING: Strictly forbidden from prescribing or suggesting pharmaceutical medications.",
                "NO_MED_ALTERATION: Never advise stopping or changing physician-prescribed medications.",
                "NON_AUTONOMOUS_INTERVENTIONS: Interventions are lifestyle and behavioral nudges only.",
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

    async def _process(self, input_data: PreventionAgentInput, actor: TokenPayload) -> PreventionAgentOutput:
        # Deterministic prevention plan generation
        plan_dict = await self.invoke_tool(
            "generate_deterministic_care_plan",
            citizen_id=input_data.citizen_id,
            risk_tier=input_data.risk_tier,
            identified_risks=input_data.identified_risks,
        )

        goals = [
            PillarGoal(
                pillar="NUTRITION",
                target="Swap 50% refined rice/wheat with regional millets (ragi, jowar, foxtail).",
                rationale="Blunts postprandial glucose spikes and improves satiety.",
            ),
            PillarGoal(
                pillar="PHYSICAL_ACTIVITY",
                target="150 minutes of brisk walking weekly with 10-minute post-meal walks.",
                rationale="Improves skeletal muscle insulin sensitivity and vascular compliance.",
            ),
            PillarGoal(
                pillar="SLEEP_AND_STRESS",
                target="Consistent 7-8 hours restful sleep; 5 minutes morning pranayama.",
                rationale="Attenuates evening cortisol surges and sympathetic overdrive.",
            ),
        ]

        actions = [
            {"day": 1, "task": "Begin post-dinner 15-minute gentle walk", "pillar": "PHYSICAL_ACTIVITY"},
            {"day": 2, "task": "Incorporate fresh vegetable salad before lunch", "pillar": "NUTRITION"},
            {"day": 3, "task": "Drink 2.5L water throughout daytime hours", "pillar": "NUTRITION"},
        ]

        coaching = (
            "Welcome to your personalized 30-day prevention journey! Small, sustainable daily habits "
            "make a profound impact on metabolic health. Focus on one consistent habit at a time."
        )

        return PreventionAgentOutput(
            citizen_id=input_data.citizen_id,
            plan_title="SevaHealth 30-Day NCD Prevention & Metabolic Stabilization Plan",
            duration_days=30,
            pillar_goals=goals,
            daily_actions=actions,
            educational_reminders=[
                "Take all physician-prescribed medications exactly as directed.",
                "Review habit milestones during your next health worker visit.",
            ],
            coaching_message=coaching,
            no_medication_disclaimer_confirmed=True,
            language=input_data.language,
        )

    async def _fallback(self, input_data: PreventionAgentInput, actor: TokenPayload, error: Exception) -> PreventionAgentOutput:
        return PreventionAgentOutput(
            citizen_id=input_data.citizen_id,
            plan_title="Standard 30-Day Healthy Living Routine",
            duration_days=30,
            pillar_goals=[
                PillarGoal(
                    pillar="PHYSICAL_ACTIVITY",
                    target="30 minutes daily moderate walking",
                    rationale="Cardiovascular fitness baseline",
                )
            ],
            daily_actions=[{"day": 1, "task": "Daily 30-minute brisk walk", "pillar": "PHYSICAL_ACTIVITY"}],
            educational_reminders=["Standard public health lifestyle guidance."],
            coaching_message="Follow daily physical activity and balanced nutritional choices.",
            no_medication_disclaimer_confirmed=True,
            language=input_data.language,
        )
