"""EscalationAgent: Bounded agent for emergency symptom detection and urgent clinical triage."""

import re
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from agents.core.base import BoundedAgent
from agents.core.models import FailureBehavior, RetryPolicy


class EscalationAgentInput(BaseModel):
    citizen_id: str
    symptom_text: str
    vitals: Dict[str, float] = Field(default_factory=dict)


class EscalationAgentOutput(BaseModel):
    citizen_id: str
    is_escalated: bool
    urgency_level: str  # EMERGENT | URGENT | ROUTINE
    trigger_rule: str
    emergency_instructions: str
    triage_case_id: Optional[str] = None
    dispatch_status: str


class EscalationAgent(BoundedAgent[EscalationAgentInput, EscalationAgentOutput]):
    """Bounded agent for acute red-flag detection and emergency dispatch."""

    RED_FLAG_PATTERNS = [
        r"\bchest\s+pain\b",
        r"\bpressure\s+in\s+chest\b",
        r"\bpain\s+radiating\s+to\s+arm\b",
        r"\bsevere\s+shortness\s+of\s+breath\b",
        r"\bcannot\s+breathe\b",
        r"\bsudden\s+weakness\b",
        r"\bslurred\s+speech\b",
        r"\bfacial\s+droop\b",
        r"\bloss\s+of\s+consciousness\b",
    ]

    def __init__(self):
        super().__init__(
            name="EscalationAgent",
            purpose=(
                "Continuously screens inputs for life-threatening acute red-flags (hypertensive crisis, "
                "myocardial infarction symptoms, acute stroke indicators). Triggers deterministic triage "
                "alerts and directs citizens to immediate emergency medical care (108). NEVER attempts to "
                "delay or manage acute emergencies in chat."
            ),
            allowed_tools=["create_emergency_alert"],
            input_schema=EscalationAgentInput,
            output_schema=EscalationAgentOutput,
            safety_constraints=[
                "FAIL_SAFE_EMERGENCY: Defaults to highest caution level if red-flags detected.",
                "NO_DELAY_TACTICS: Never advises waiting or self-monitoring during acute chest pain.",
                "URGENT_HANDOFF: Automatically creates triage case for on-call medical staff.",
            ],
            authorized_roles=[
                UserRole.CITIZEN,
                UserRole.HEALTH_WORKER,
                UserRole.CLINICIAN,
                UserRole.SYSTEM_ADMIN,
            ],
            timeout_sec=3.0,
            retry_policy=RetryPolicy(max_retries=1, initial_delay_ms=100),
            failure_behavior=FailureBehavior.ESCALATE_TO_CLINICIAN,
        )

    async def _process(self, input_data: EscalationAgentInput, actor: TokenPayload) -> EscalationAgentOutput:
        symptom_str = input_data.symptom_text.lower()
        systolic_bp = input_data.vitals.get("systolic_bp", 120.0)

        is_red_flag = any(re.search(pat, symptom_str) for pat in self.RED_FLAG_PATTERNS)
        is_hypertensive_crisis = systolic_bp >= 180.0

        if is_red_flag or is_hypertensive_crisis:
            urgency = "EMERGENT"
            reason = "Acute Cardiovascular / Neurological Red-Flag" if is_red_flag else f"Hypertensive Crisis (Systolic BP {systolic_bp} mmHg)"

            alert_res = await self.invoke_tool(
                "create_emergency_alert",
                citizen_id=input_data.citizen_id,
                urgency=urgency,
                reason=reason,
            )

            instructions = (
                "EMERGENCY ALERT: Your reported symptoms require IMMEDIATE medical attention. "
                "Please call 108 or proceed to the nearest emergency hospital casualty ward immediately. "
                "Do not drive yourself. An on-call medical alert has been routed to your care team."
            )

            return EscalationAgentOutput(
                citizen_id=input_data.citizen_id,
                is_escalated=True,
                urgency_level=urgency,
                trigger_rule=reason,
                emergency_instructions=instructions,
                triage_case_id=alert_res.get("triage_id"),
                dispatch_status="EMERGENCY_DISPATCH_TRIGGERED",
            )

        return EscalationAgentOutput(
            citizen_id=input_data.citizen_id,
            is_escalated=False,
            urgency_level="ROUTINE",
            trigger_rule="No acute red flags detected in current assessment",
            emergency_instructions="Continue routine preventive care. Call 108 if acute symptoms develop.",
            triage_case_id=None,
            dispatch_status="ROUTINE_STANDBY",
        )

    async def _fallback(self, input_data: EscalationAgentInput, actor: TokenPayload, error: Exception) -> EscalationAgentOutput:
        # Safe fallback: Always escalate to clinician if escalation evaluator failed
        return EscalationAgentOutput(
            citizen_id=input_data.citizen_id,
            is_escalated=True,
            urgency_level="URGENT",
            trigger_rule="Fail-safe escalation triggered due to processing interruption",
            emergency_instructions="If experiencing severe discomfort, seek emergency medical care immediately.",
            triage_case_id="failsafe_triage_001",
            dispatch_status="FAILSAFE_CLINICIAN_ALERT",
        )
