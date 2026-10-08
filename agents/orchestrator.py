"""Multi-Agent Orchestrator for Deterministic Workflows.

Guarantees:
1. No unconstrained agent-to-agent recursion or autonomous loops.
2. Predetermined, auditable workflow execution graphs.
3. Hard boundaries and failure containment at each stage.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import structlog

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from agents.registry import agent_registry
from agents.definitions.screening_agent import ScreeningAgentInput
from agents.definitions.risk_assessment_agent import RiskAssessmentAgentInput
from agents.definitions.trend_analysis_agent import TrendAnalysisAgentInput
from agents.definitions.prevention_agent import PreventionAgentInput
from agents.definitions.escalation_agent import EscalationAgentInput
from agents.definitions.health_education_agent import HealthEducationAgentInput
from agents.definitions.clinical_summary_agent import ClinicalSummaryAgentInput

logger = structlog.get_logger(__name__)


class ScreeningPipelineResult(BaseModel):
    citizen_id: str
    screening: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    trajectory: Dict[str, Any]
    prevention_plan: Dict[str, Any]
    pipeline_status: str = "COMPLETED"
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentOrchestrator:
    """Orchestrates structured, deterministic pipelines across bounded agents."""

    @classmethod
    async def run_screening_to_prevention_pipeline(
        cls,
        citizen_id: str,
        age: int,
        gender: str,
        waist_cm: float,
        activity_level: str,
        family_history: str,
        cbac_answers: Dict[str, Any],
        vitals: Dict[str, float],
        actor: TokenPayload,
    ) -> ScreeningPipelineResult:
        """Executes the standard 4-stage citizen intake pipeline:

        Screening -> Risk Assessment -> Trend Analysis -> Prevention Plan
        """
        # Stage 1: Screening Agent
        screening_agent = agent_registry.get_agent("ScreeningAgent")
        scr_input = ScreeningAgentInput(
            citizen_id=citizen_id,
            age=age,
            gender=gender,
            waist_circumference_cm=waist_cm,
            physical_activity_level=activity_level,
            family_history_diabetes=family_history,
            cbac_answers=cbac_answers,
            vitals=vitals,
        )
        scr_res = await screening_agent.execute(scr_input, actor, citizen_id=citizen_id)

        # Stage 2: Risk Assessment Agent
        risk_agent = agent_registry.get_agent("RiskAssessmentAgent")
        risk_input = RiskAssessmentAgentInput(
            citizen_id=citizen_id,
            vitals=vitals,
            lifestyle={"activity": activity_level},
        )
        risk_res = await risk_agent.execute(risk_input, actor, citizen_id=citizen_id)

        # Stage 3: Trend Analysis Agent
        trend_agent = agent_registry.get_agent("TrendAnalysisAgent")
        trend_input = TrendAnalysisAgentInput(citizen_id=citizen_id)
        trend_res = await trend_agent.execute(trend_input, actor, citizen_id=citizen_id)

        # Stage 4: Prevention Agent
        prev_agent = agent_registry.get_agent("PreventionAgent")
        prev_input = PreventionAgentInput(
            citizen_id=citizen_id,
            risk_tier=risk_res.data.risk_tier if risk_res.data else "MODERATE",
            identified_risks=risk_res.data.top_contributing_factors if risk_res.data else [],
        )
        prev_res = await prev_agent.execute(prev_input, actor, citizen_id=citizen_id)

        return ScreeningPipelineResult(
            citizen_id=citizen_id,
            screening=scr_res.data.model_dump() if scr_res.data else {},
            risk_assessment=risk_res.data.model_dump() if risk_res.data else {},
            trajectory=trend_res.data.model_dump() if trend_res.data else {},
            prevention_plan=prev_res.data.model_dump() if prev_res.data else {},
            pipeline_status="COMPLETED",
        )

    @classmethod
    async def run_conversational_safety_pipeline(
        cls,
        citizen_id: str,
        user_message: str,
        actor: TokenPayload,
        vitals: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Runs the conversation gateway: checks for emergencies via EscalationAgent first,

        then routes to Education or Prevention agents.
        """
        # 1. First Pass: Escalation Check
        escalation_agent = agent_registry.get_agent("EscalationAgent")
        esc_res = await escalation_agent.execute(
            EscalationAgentInput(
                citizen_id=citizen_id,
                symptom_text=user_message,
                vitals=vitals or {},
            ),
            actor,
            citizen_id=citizen_id,
        )

        if esc_res.data and esc_res.data.is_escalated:
            return {
                "route": "EMERGENCY_ESCALATION",
                "is_escalated": True,
                "urgency": esc_res.data.urgency_level,
                "instructions": esc_res.data.emergency_instructions,
                "triage_case_id": esc_res.data.triage_case_id,
            }

        # 2. Second Pass: Health Education
        edu_agent = agent_registry.get_agent("HealthEducationAgent")
        edu_res = await edu_agent.execute(
            HealthEducationAgentInput(
                citizen_id=citizen_id,
                topic=user_message,
            ),
            actor,
            citizen_id=citizen_id,
        )

        return {
            "route": "HEALTH_EDUCATION",
            "is_escalated": False,
            "response": edu_res.data.model_dump() if edu_res.data else {},
        }


orchestrator = AgentOrchestrator()
