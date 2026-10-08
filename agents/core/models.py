"""Core Data Models and Contracts for SevaHealth Bounded Multi-Agent System."""

from enum import Enum
from typing import Dict, List, Optional, Any, Type, Generic, TypeVar
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid

from packages.types.enums import UserRole


class FailureBehavior(str, Enum):
    """Deterministic failure behavior when LLM is unavailable or times out."""
    FALLBACK_TO_DETERMINISTIC = "FALLBACK_TO_DETERMINISTIC"  # Run deterministic algorithm / rule engine
    FAIL_SAFE_DEGRADED = "FAIL_SAFE_DEGRADED"                # Return cached / standard guidance with safety notice
    ESCALATE_TO_CLINICIAN = "ESCALATE_TO_CLINICIAN"          # Flag case to human triage queue immediately
    RETURN_SAFE_ERROR = "RETURN_SAFE_ERROR"                  # Structured graceful error without clinical guidance


class AgentStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    DISABLED = "DISABLED"


class RetryPolicy(BaseModel):
    """Configurable retry policy with exponential backoff."""
    max_retries: int = Field(default=2, ge=0, le=5)
    initial_delay_ms: int = Field(default=200, ge=50)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)
    retryable_exceptions: List[str] = Field(
        default_factory=lambda: ["TimeoutError", "RateLimitError", "APIConnectionError"]
    )


class AgentMetadata(BaseModel):
    """Introspectable metadata and contract defining a bounded agent."""
    name: str
    purpose: str
    allowed_tools: List[str]
    input_schema_name: str
    output_schema_name: str
    safety_constraints: List[str]
    authorized_roles: List[UserRole]
    timeout_sec: float
    retry_policy: RetryPolicy
    failure_behavior: FailureBehavior
    status: AgentStatus = AgentStatus.OPERATIONAL
    is_autonomous: bool = False  # Strictly bounded, NEVER autonomous


class AgentExecutionLog(BaseModel):
    """Forensic audit record for an individual agent execution."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_name: str
    actor_id: str
    actor_role: str
    citizen_id: Optional[str] = None
    input_summary: Dict[str, Any]
    tools_called: List[str] = Field(default_factory=list)
    deterministic_services_invoked: List[str] = Field(default_factory=list)
    llm_invoked: bool = False
    duration_ms: float = 0.0
    status: str = "SUCCESS"  # SUCCESS | RETRIED | FALLBACK_USED | ERROR
    fallback_used: bool = False
    error_message: Optional[str] = None
    safety_disclaimer_attached: bool = True


TOutput = TypeVar("TOutput")


class BoundedAgentResult(BaseModel, Generic[TOutput]):
    """Standardized response returned by any BoundedAgent execution."""
    execution_id: str
    agent_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool
    data: Optional[TOutput] = None
    fallback_used: bool = False
    deterministic_computation_provenance: Dict[str, str] = Field(default_factory=dict)
    disclaimer: str = (
        "AI-ASSISTED PREVENTIVE HEALTH INTELLIGENCE: Risk estimations and explanations are non-diagnostic. "
        "Clinical review required before medication or therapeutic changes."
    )
    audit_trace_id: str
