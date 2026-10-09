"""Asynchronous Telemetry Buffer for SevaHealth AI.

Adapted and extended from bezs-observability watcher_sdk.
Guarantees non-blocking event collection with correlation tagging and PHI sanitization.
"""

import time
import asyncio
from typing import List, Dict, Any, Optional
import structlog

from packages.observability.context import CorrelationContext
from packages.observability.sanitizer import HealthcareLogSanitizer
from packages.observability.metrics import metrics

logger = structlog.get_logger(__name__)


class TelemetryEvent:
    def __init__(self, event_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None):
        self.event_type = event_type
        self.correlation_id = correlation_id or CorrelationContext.get_correlation_id()
        self.trace_id = CorrelationContext.get_trace_id()
        self.stage = CorrelationContext.get_current_stage().value
        self.timestamp = time.time()
        # Always sanitize payload to uphold PHI safety rules
        self.payload = HealthcareLogSanitizer.sanitize_data(payload)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "stage": self.stage,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


class AsyncTelemetryBuffer:
    """Non-blocking asynchronous event buffer (adapted from bezs-observability watcher_sdk)."""

    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self._buffer: List[TelemetryEvent] = []
        self._history: List[TelemetryEvent] = []  # Retains recent events for trace correlation
        self._lock = asyncio.Lock()

    async def emit(self, event_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None):
        event = TelemetryEvent(event_type, payload, correlation_id)
        async with self._lock:
            if len(self._buffer) >= self.max_buffer_size:
                self._buffer.pop(0)
            self._buffer.append(event)

            if len(self._history) >= self.max_buffer_size:
                self._history.pop(0)
            self._history.append(event)

        logger.debug("telemetry_event_buffered", event_type=event_type, correlation_id=event.correlation_id)

    async def flush(self) -> List[TelemetryEvent]:
        async with self._lock:
            flushed = list(self._buffer)
            self._buffer.clear()
            return flushed

    async def get_recent_events(self, limit: int = 100, correlation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        async with self._lock:
            events = self._history
            if correlation_id:
                events = [e for e in events if e.correlation_id == correlation_id]
            return [e.to_dict() for e in events[-limit:]]


# Global singleton instance
telemetry_buffer = AsyncTelemetryBuffer()
