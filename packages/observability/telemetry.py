import time
import asyncio
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class TelemetryEvent:
    def __init__(self, event_type: str, payload: Dict[str, Any]):
        self.event_type = event_type
        self.payload = payload
        self.timestamp = time.time()


class AsyncTelemetryBuffer:
    """Non-blocking asynchronous event buffer (adapted from bezs-observability watcher_sdk)."""

    def __init__(self, max_buffer_size: int = 500):
        self.max_buffer_size = max_buffer_size
        self._buffer: List[TelemetryEvent] = []
        self._lock = asyncio.Lock()

    async def emit(self, event_type: str, payload: Dict[str, Any]):
        event = TelemetryEvent(event_type, payload)
        async with self._lock:
            if len(self._buffer) >= self.max_buffer_size:
                # Discard oldest to avoid memory leaks
                self._buffer.pop(0)
            self._buffer.append(event)
        logger.debug("telemetry_event_buffered", event_type=event_type)

    async def flush(self) -> List[TelemetryEvent]:
        async with self._lock:
            flushed = list(self._buffer)
            self._buffer.clear()
            return flushed


# Global singleton instance
telemetry_buffer = AsyncTelemetryBuffer()
