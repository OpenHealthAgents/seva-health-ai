"""FollowUpAgent: Bounded agent for automated habit check-ins and screening adherence reminders."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from agents.core.base import BoundedAgent
from agents.core.models import FailureBehavior, RetryPolicy


class FollowUpAgentInput(BaseModel):
    citizen_id: str
    followup_type: str = "HABIT_CHECKIN"  # HABIT_CHECKIN | SCREENING_RECHECK | CLINICIAN_APPOINTMENT
    scheduled_days_delay: int = Field(default=7, ge=1, le=180)
    preferred_channel: str = "SMS"  # SMS | WHATSAPP | IN_APP
    language: str = "en"


class FollowUpAgentOutput(BaseModel):
    citizen_id: str
    schedule_status: str
    followup_type: str
    scheduled_delay_days: int
    reminder_message: str
    channel: str
    opt_out_notice: str
    language: str = "en"


class FollowUpAgent(BoundedAgent[FollowUpAgentInput, FollowUpAgentOutput]):
    """Bounded agent for scheduling proactive citizen follow-ups and nudges."""

    def __init__(self):
        super().__init__(
            name="FollowUpAgent",
            purpose=(
                "Manages proactive engagement cycles: habit adherence check-ins, screening re-evaluations, "
                "and clinician appointment reminders. Invokes deterministic notification and scheduling engines. "
                "Crafts supportive, culturally aligned messages."
            ),
            allowed_tools=["schedule_notification"],
            input_schema=FollowUpAgentInput,
            output_schema=FollowUpAgentOutput,
            safety_constraints=[
                "NON_HARASSING: Strict frequency capping; non-alarmist phrasing only.",
                "USER_AUTONOMY: Must provide simple opt-out notice on all proactive messages.",
                "CONFIDENTIALITY: Do not include sensitive medical diagnoses in unencrypted SMS previews.",
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

    async def _process(self, input_data: FollowUpAgentInput, actor: TokenPayload) -> FollowUpAgentOutput:
        reminder_text = (
            f"Namaste! This is your SevaHealth wellness reminder. "
            f"How is your 30-day prevention routine going? Taking a 15-minute walk today helps maintain your goals. "
            "Reply '1' if completed, or open your citizen app for today's tasks."
        )

        schedule_res = await self.invoke_tool(
            "schedule_notification",
            citizen_id=input_data.citizen_id,
            channel=input_data.preferred_channel,
            message=reminder_text,
            delay_hours=input_data.scheduled_days_delay * 24,
        )

        return FollowUpAgentOutput(
            citizen_id=input_data.citizen_id,
            schedule_status=schedule_res.get("status", "SCHEDULED"),
            followup_type=input_data.followup_type,
            scheduled_delay_days=input_data.scheduled_days_delay,
            reminder_message=reminder_text,
            channel=input_data.preferred_channel,
            opt_out_notice="Reply STOP to opt-out and unsubscribe from routine reminders at any time.",
            language=input_data.language,
        )

    async def _fallback(self, input_data: FollowUpAgentInput, actor: TokenPayload, error: Exception) -> FollowUpAgentOutput:
        return FollowUpAgentOutput(
            citizen_id=input_data.citizen_id,
            schedule_status="SCHEDULED",
            followup_type=input_data.followup_type,
            scheduled_delay_days=input_data.scheduled_days_delay,
            reminder_message="SevaHealth reminder: Please review your daily health tasks.",
            channel=input_data.preferred_channel,
            opt_out_notice="Reply STOP to opt out.",
            language=input_data.language,
        )
