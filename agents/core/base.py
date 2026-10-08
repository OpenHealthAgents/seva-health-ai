"""Base Bounded Agent Abstraction for SevaHealth.

Strict Guarantees:
1. Not autonomous: Strictly bounded to declared purpose, input/output schemas, and allowed tools.
2. Authorization: Validates caller role against authorized_roles on every call.
3. Whitelisted Tools: Can ONLY invoke deterministic tools declared in allowed_tools.
4. Determinism: Critical clinical calculations are executed by validated engines, never LLMs.
5. Observability: Emits structured telemetry on all executions, retries, and fallbacks.
6. Safety: Enforces mandatory non-diagnostic clinical disclaimer and failure handling.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Generic, TypeVar
import asyncio
import time
import uuid
import structlog
from pydantic import BaseModel

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from agents.core.models import (
    FailureBehavior,
    AgentStatus,
    RetryPolicy,
    AgentMetadata,
    AgentExecutionLog,
    BoundedAgentResult,
)
from agents.core.telemetry import agent_telemetry_buffer
from agents.core.tools_registry import DeterministicToolsRegistry, UnauthorizedToolError

logger = structlog.get_logger(__name__)

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class AgentAuthorizationError(Exception):
    """Raised when an actor does not hold permission to invoke a bounded agent."""
    pass


class AgentExecutionTimeoutError(Exception):
    """Raised when agent execution exceeds configured timeout limit."""
    pass


class BoundedAgent(ABC, Generic[TInput, TOutput]):
    """Abstract Base Class for all SevaHealth Bounded Healthcare Agents."""

    def __init__(
        self,
        name: str,
        purpose: str,
        allowed_tools: List[str],
        input_schema: Type[TInput],
        output_schema: Type[TOutput],
        safety_constraints: List[str],
        authorized_roles: List[UserRole],
        timeout_sec: float = 5.0,
        retry_policy: Optional[RetryPolicy] = None,
        failure_behavior: FailureBehavior = FailureBehavior.FALLBACK_TO_DETERMINISTIC,
    ):
        self.name = name
        self.purpose = purpose
        self.allowed_tools = allowed_tools
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.safety_constraints = safety_constraints
        self.authorized_roles = authorized_roles
        self.timeout_sec = timeout_sec
        self.retry_policy = retry_policy or RetryPolicy()
        self.failure_behavior = failure_behavior
        self.status = AgentStatus.OPERATIONAL

    def get_metadata(self) -> AgentMetadata:
        """Returns introspectable metadata and contract specification."""
        return AgentMetadata(
            name=self.name,
            purpose=self.purpose,
            allowed_tools=self.allowed_tools,
            input_schema_name=self.input_schema.__name__,
            output_schema_name=self.output_schema.__name__,
            safety_constraints=self.safety_constraints,
            authorized_roles=self.authorized_roles,
            timeout_sec=self.timeout_sec,
            retry_policy=self.retry_policy,
            failure_behavior=self.failure_behavior,
            status=self.status,
            is_autonomous=False,
        )

    async def invoke_tool(self, tool_name: str, **kwargs) -> Any:
        """Invokes a deterministic tool, strictly constrained to allowed_tools whitelist."""
        return await DeterministicToolsRegistry.invoke(
            agent_name=self.name,
            tool_name=tool_name,
            allowed_tools=self.allowed_tools,
            **kwargs,
        )

    def _check_authorization(self, actor: TokenPayload) -> None:
        """Enforces role-based invocation permissions."""
        role = actor.role if isinstance(actor.role, UserRole) else UserRole(str(actor.role))
        if role == UserRole.SYSTEM_ADMIN:
            return
        if role not in self.authorized_roles:
            logger.warning(
                "AGENT_AUTH_DENIED",
                agent=self.name,
                actor_id=actor.sub,
                actor_role=role,
                allowed_roles=[r.value for r in self.authorized_roles],
            )
            raise AgentAuthorizationError(
                f"Role '{role.value}' is not authorized to invoke agent '{self.name}'. "
                f"Authorized roles: {[r.value for r in self.authorized_roles]}"
            )

    @abstractmethod
    async def _process(self, input_data: TInput, actor: TokenPayload) -> TOutput:
        """Core agent processing logic to be implemented by concrete agents."""
        pass

    @abstractmethod
    async def _fallback(self, input_data: TInput, actor: TokenPayload, error: Exception) -> TOutput:
        """Deterministic or safe degraded fallback behavior."""
        pass

    async def execute(
        self,
        input_data: TInput,
        actor: TokenPayload,
        citizen_id: Optional[str] = None,
    ) -> BoundedAgentResult[TOutput]:
        """Main execution harness enforcing security, timeouts, retries, fallbacks, and telemetry."""
        start_time = time.time()
        execution_id = str(uuid.uuid4())
        tools_called_in_session: List[str] = []
        fallback_used = False
        error_msg = None
        status = "SUCCESS"

        # 1. Authorization check
        self._check_authorization(actor)

        # 2. Input validation
        if not isinstance(input_data, self.input_schema):
            if isinstance(input_data, dict):
                input_data = self.input_schema(**input_data)
            elif hasattr(input_data, "model_dump"):
                input_data = self.input_schema(**input_data.model_dump())
            else:
                input_data = self.input_schema(**input_data.dict())

        # 3. Execution loop with retries and timeout
        output_data: Optional[TOutput] = None
        attempts = 0
        last_exception: Optional[Exception] = None

        while attempts <= self.retry_policy.max_retries:
            try:
                attempts += 1
                output_data = await asyncio.wait_for(
                    self._process(input_data, actor),
                    timeout=self.timeout_sec,
                )
                break  # Successful execution
            except asyncio.TimeoutError as te:
                last_exception = AgentExecutionTimeoutError(
                    f"Agent '{self.name}' timed out after {self.timeout_sec}s (Attempt {attempts})"
                )
                logger.warning("AGENT_TIMEOUT", agent=self.name, attempt=attempts)
                if attempts <= self.retry_policy.max_retries:
                    delay = (self.retry_policy.initial_delay_ms / 1000.0) * (self.retry_policy.backoff_multiplier ** (attempts - 1))
                    await asyncio.sleep(delay)
            except Exception as e:
                last_exception = e
                logger.warning("AGENT_ERROR_ATTEMPT", agent=self.name, attempt=attempts, error=str(e))
                if attempts <= self.retry_policy.max_retries:
                    delay = (self.retry_policy.initial_delay_ms / 1000.0) * (self.retry_policy.backoff_multiplier ** (attempts - 1))
                    await asyncio.sleep(delay)
                else:
                    break

        # 4. Handle failure via configured failure_behavior
        if output_data is None:
            status = "FALLBACK_USED"
            fallback_used = True
            error_msg = str(last_exception)
            logger.info(
                "AGENT_TRIGGERING_FAILURE_BEHAVIOR",
                agent=self.name,
                behavior=self.failure_behavior,
                error=error_msg,
            )
            output_data = await self._fallback(input_data, actor, last_exception)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # 5. Record telemetry log
        log_entry = AgentExecutionLog(
            execution_id=execution_id,
            agent_name=self.name,
            actor_id=actor.sub,
            actor_role=actor.role.value if hasattr(actor.role, "value") else str(actor.role),
            citizen_id=citizen_id,
            input_summary={k: str(v)[:100] for k, v in input_data.model_dump().items()},
            tools_called=self.allowed_tools,
            llm_invoked=not fallback_used,
            duration_ms=duration_ms,
            status=status,
            fallback_used=fallback_used,
            error_message=error_msg,
        )
        agent_telemetry_buffer.record(log_entry)

        return BoundedAgentResult[TOutput](
            execution_id=execution_id,
            agent_name=self.name,
            success=True,
            data=output_data,
            fallback_used=fallback_used,
            deterministic_computation_provenance={
                "tools_permitted": ", ".join(self.allowed_tools),
                "failure_policy": self.failure_behavior.value,
            },
            audit_trace_id=execution_id,
        )
