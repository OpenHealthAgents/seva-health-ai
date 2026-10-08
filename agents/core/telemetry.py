"""Observability and Audit Logging for Multi-Agent Executions."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import structlog
from agents.core.models import AgentExecutionLog

logger = structlog.get_logger(__name__)


class AgentTelemetryBuffer:
    """In-memory telemetry and forensic audit buffer for bounded agents."""

    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self._logs: List[AgentExecutionLog] = []

    def record(self, log: AgentExecutionLog) -> None:
        self._logs.append(log)
        if len(self._logs) > self.max_buffer_size:
            self._logs.pop(0)

        logger.info(
            "AGENT_EXECUTION_AUDIT",
            execution_id=log.execution_id,
            agent=log.agent_name,
            actor_id=log.actor_id,
            role=log.actor_role,
            citizen_id=log.citizen_id,
            duration_ms=log.duration_ms,
            status=log.status,
            fallback=log.fallback_used,
            tools=log.tools_called,
        )

    def get_logs(
        self,
        agent_name: Optional[str] = None,
        citizen_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AgentExecutionLog]:
        logs = self._logs
        if agent_name:
            logs = [l for l in logs if l.agent_name == agent_name]
        if citizen_id:
            logs = [l for l in logs if l.citizen_id == citizen_id]
        return logs[-limit:]

    def clear(self) -> None:
        self._logs.clear()


agent_telemetry_buffer = AgentTelemetryBuffer()
