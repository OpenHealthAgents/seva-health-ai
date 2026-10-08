"""Central Agent Registry for SevaHealth Bounded Multi-Agent System."""

from typing import Dict, List, Optional, Any
import structlog

from packages.auth.jwt import TokenPayload
from agents.core.base import BoundedAgent
from agents.core.models import AgentMetadata, BoundedAgentResult
from agents.definitions.screening_agent import ScreeningAgent
from agents.definitions.risk_assessment_agent import RiskAssessmentAgent
from agents.definitions.trend_analysis_agent import TrendAnalysisAgent
from agents.definitions.prevention_agent import PreventionAgent
from agents.definitions.health_education_agent import HealthEducationAgent
from agents.definitions.followup_agent import FollowUpAgent
from agents.definitions.clinical_summary_agent import ClinicalSummaryAgent
from agents.definitions.escalation_agent import EscalationAgent
from agents.definitions.population_health_agent import PopulationHealthAgent

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """Singleton Registry managing instances and introspection of all 9 bounded agents."""

    def __init__(self):
        self._agents: Dict[str, BoundedAgent] = {
            "ScreeningAgent": ScreeningAgent(),
            "RiskAssessmentAgent": RiskAssessmentAgent(),
            "TrendAnalysisAgent": TrendAnalysisAgent(),
            "PreventionAgent": PreventionAgent(),
            "HealthEducationAgent": HealthEducationAgent(),
            "FollowUpAgent": FollowUpAgent(),
            "ClinicalSummaryAgent": ClinicalSummaryAgent(),
            "EscalationAgent": EscalationAgent(),
            "PopulationHealthAgent": PopulationHealthAgent(),
        }

    def get_agent(self, name: str) -> BoundedAgent:
        """Retrieves a bounded agent by name."""
        if name not in self._agents:
            raise KeyError(
                f"Agent '{name}' not found in registry. Registered agents: {list(self._agents.keys())}"
            )
        return self._agents[name]

    def list_agents(self) -> List[AgentMetadata]:
        """Returns metadata specifications for all 9 registered bounded agents."""
        return [agent.get_metadata() for agent in self._agents.values()]

    def list_agent_names(self) -> List[str]:
        return list(self._agents.keys())

    async def execute_agent(
        self,
        name: str,
        input_payload: Dict[str, Any],
        actor: TokenPayload,
        citizen_id: Optional[str] = None,
    ) -> BoundedAgentResult:
        """Executes a named agent with provided payload and actor token."""
        agent = self.get_agent(name)
        typed_input = agent.input_schema(**input_payload)
        return await agent.execute(
            input_data=typed_input,
            actor=actor,
            citizen_id=citizen_id,
        )

    def get_system_health(self) -> Dict[str, Any]:
        """Returns operational status across all 9 agents."""
        return {
            "total_agents": len(self._agents),
            "status": "OPERATIONAL",
            "agents": {
                name: {
                    "purpose": agent.purpose[:60] + "...",
                    "allowed_tools": agent.allowed_tools,
                    "authorized_roles": [r.value for r in agent.authorized_roles],
                    "timeout_sec": agent.timeout_sec,
                    "failure_behavior": agent.failure_behavior.value,
                    "is_autonomous": False,
                }
                for name, agent in self._agents.items()
            }
        }


# Global registry singleton
agent_registry = AgentRegistry()
