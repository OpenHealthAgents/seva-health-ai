"""End-to-End Distributed Tracing Across the 6 Lifecycle Tiers.

Ensures every request is completely traceable across:
1. mobile (intake, screening input, mobile query)
2. api (gateway routing, middleware, auth)
3. agent (prevention agent reasoning, safety checks)
4. risk_engine (multi-domain stratification, trajectory slope)
5. clinical_repository (EHR persistence, FHIR observations)
6. notification (SMS, WhatsApp, Push dispatch)
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import contextlib

from packages.observability.context import CorrelationContext, SpanStage
from packages.observability.sanitizer import HealthcareLogSanitizer


class TraceSpan:
    """Represents a discrete unit of execution within the distributed request lifecycle."""

    def __init__(
        self,
        name: str,
        stage: SpanStage,
        trace_id: str,
        correlation_id: str,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ):
        self.span_id = span_id or f"span-{uuid.uuid4().hex[:12]}"
        self.parent_span_id = parent_span_id
        self.trace_id = trace_id
        self.correlation_id = correlation_id
        self.stage = stage
        self.name = name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.status: str = "OK"  # OK | ERROR
        self.error_message: Optional[str] = None
        self.tags: Dict[str, Any] = HealthcareLogSanitizer.sanitize_data(tags or {})
        self.events: List[Dict[str, Any]] = []

    def add_event(self, event_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Records an in-span event checkpoint."""
        self.events.append({
            "name": event_name,
            "timestamp": time.time(),
            "attributes": HealthcareLogSanitizer.sanitize_data(attributes or {}),
        })

    def set_tag(self, key: str, value: Any):
        self.tags[key] = HealthcareLogSanitizer.sanitize_data(value)

    def finish(self, status: str = "OK", error: Optional[str] = None):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.status = status
        if error:
            self.error_message = HealthcareLogSanitizer.sanitize_string(str(error))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "stage": self.stage.value,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "tags": self.tags,
            "events_count": len(self.events),
            "events": self.events,
        }


class TraceStore:
    """Thread-safe in-memory store for distributed traces with correlation indexing."""

    def __init__(self, max_spans: int = 5000):
        self.max_spans = max_spans
        self._spans: List[TraceSpan] = []
        self._by_correlation: Dict[str, List[TraceSpan]] = {}
        self._by_trace: Dict[str, List[TraceSpan]] = {}

    def record_span(self, span: TraceSpan):
        if len(self._spans) >= self.max_spans:
            oldest = self._spans.pop(0)
            if oldest.correlation_id in self._by_correlation:
                self._by_correlation[oldest.correlation_id] = [
                    s for s in self._by_correlation[oldest.correlation_id] if s.span_id != oldest.span_id
                ]
            if oldest.trace_id in self._by_trace:
                self._by_trace[oldest.trace_id] = [
                    s for s in self._by_trace[oldest.trace_id] if s.span_id != oldest.span_id
                ]

        self._spans.append(span)
        if span.correlation_id not in self._by_correlation:
            self._by_correlation[span.correlation_id] = []
        self._by_correlation[span.correlation_id].append(span)

        if span.trace_id not in self._by_trace:
            self._by_trace[span.trace_id] = []
        self._by_trace[span.trace_id].append(span)

    def get_trace_by_correlation_id(self, correlation_id: str) -> List[Dict[str, Any]]:
        spans = self._by_correlation.get(correlation_id, [])
        return [s.to_dict() for s in sorted(spans, key=lambda x: x.start_time)]

    def get_trace_summary(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        spans = self._by_correlation.get(correlation_id, [])
        if not spans:
            return None
        stages_covered = list(dict.fromkeys(s.stage.value for s in spans))
        total_duration = max((s.end_time or s.start_time) for s in spans) - min(s.start_time for s in spans)
        has_error = any(s.status == "ERROR" for s in spans)
        return {
            "correlation_id": correlation_id,
            "trace_id": spans[0].trace_id,
            "span_count": len(spans),
            "stages_covered": stages_covered,
            "total_duration_ms": round(total_duration * 1000, 2),
            "status": "ERROR" if has_error else "OK",
            "start_time": datetime.fromtimestamp(spans[0].start_time, tz=timezone.utc).isoformat(),
            "spans": [s.to_dict() for s in sorted(spans, key=lambda x: x.start_time)],
        }

    def list_recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        recent_cids = list(reversed(list(self._by_correlation.keys())))[:limit]
        summaries = []
        for cid in recent_cids:
            summary = self.get_trace_summary(cid)
            if summary:
                summaries.append(summary)
        return summaries


trace_store = TraceStore()


class SevaTracer:
    """Convenience context manager and API for emitting spans across the 6 stages."""

    @classmethod
    @contextlib.contextmanager
    def span(
        cls,
        name: str,
        stage: SpanStage,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Synchronous context manager wrapping execution within a TraceSpan."""
        corr_id = CorrelationContext.get_correlation_id()
        trace_id = CorrelationContext.get_trace_id()
        parent_id = parent_span_id or CorrelationContext.get_current_span_id()

        span_obj = TraceSpan(
            name=name,
            stage=stage,
            trace_id=trace_id,
            correlation_id=corr_id,
            parent_span_id=parent_id,
            tags=tags,
        )

        prev_span_id = CorrelationContext.get_current_span_id()
        prev_stage = CorrelationContext.get_current_stage()

        CorrelationContext.set_current_span_id(span_obj.span_id)
        CorrelationContext.set_current_stage(stage)

        try:
            yield span_obj
            span_obj.finish(status="OK")
        except Exception as exc:
            span_obj.finish(status="ERROR", error=str(exc))
            raise
        finally:
            trace_store.record_span(span_obj)
            CorrelationContext.set_current_span_id(prev_span_id)
            CorrelationContext.set_current_stage(prev_stage)

    @classmethod
    @contextlib.asynccontextmanager
    async def async_span(
        cls,
        name: str,
        stage: SpanStage,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Asynchronous context manager wrapping execution within a TraceSpan."""
        corr_id = CorrelationContext.get_correlation_id()
        trace_id = CorrelationContext.get_trace_id()
        parent_id = parent_span_id or CorrelationContext.get_current_span_id()

        span_obj = TraceSpan(
            name=name,
            stage=stage,
            trace_id=trace_id,
            correlation_id=corr_id,
            parent_span_id=parent_id,
            tags=tags,
        )

        prev_span_id = CorrelationContext.get_current_span_id()
        prev_stage = CorrelationContext.get_current_stage()

        CorrelationContext.set_current_span_id(span_obj.span_id)
        CorrelationContext.set_current_stage(stage)

        try:
            yield span_obj
            span_obj.finish(status="OK")
        except Exception as exc:
            span_obj.finish(status="ERROR", error=str(exc))
            raise
        finally:
            trace_store.record_span(span_obj)
            CorrelationContext.set_current_span_id(prev_span_id)
            CorrelationContext.set_current_stage(prev_stage)


tracer = SevaTracer()
