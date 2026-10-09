"""Correlation ID and Distributed Tracing Context for SevaHealth AI.

Tracks and propagates request correlation IDs, trace IDs, and span hierarchies
across all 6 tiers: Mobile -> API -> Agent -> Risk Engine -> Clinical Repo -> Notification.
"""

import uuid
import contextvars
from typing import Optional, Dict, Any
from enum import Enum


class SpanStage(str, Enum):
    """The 6 traceable stages in the SevaHealth AI request lifecycle."""
    MOBILE = "mobile"
    API = "api"
    AGENT = "agent"
    RISK_ENGINE = "risk_engine"
    CLINICAL_REPOSITORY = "clinical_repository"
    NOTIFICATION = "notification"


# Context variables for async execution context propagation
_correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)
_trace_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)
_parent_span_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "parent_span_id", default=None
)
_current_span_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_span_id", default=None
)
_current_stage_ctx: contextvars.ContextVar[SpanStage] = contextvars.ContextVar(
    "current_stage", default=SpanStage.API
)
_client_platform_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "client_platform", default="unknown"
)


class CorrelationContext:
    """Helper for reading, generating, and propagating trace context."""

    CORRELATION_ID_HEADER = "X-Correlation-ID"
    REQUEST_ID_HEADER = "X-Request-ID"
    TRACE_ID_HEADER = "X-Trace-ID"
    SPAN_ID_HEADER = "X-Span-ID"
    CLIENT_PLATFORM_HEADER = "X-Client-Platform"

    @classmethod
    def get_correlation_id(cls) -> str:
        """Retrieves active correlation ID, or generates a new one if unset."""
        cid = _correlation_id_ctx.get()
        if not cid:
            cid = f"seva-corr-{uuid.uuid4().hex[:12]}"
            _correlation_id_ctx.set(cid)
        return cid

    @classmethod
    def set_correlation_id(cls, cid: Optional[str]) -> str:
        """Sets active correlation ID, generating a fallback if None or empty."""
        final_cid = cid.strip() if cid and cid.strip() else f"seva-corr-{uuid.uuid4().hex[:12]}"
        _correlation_id_ctx.set(final_cid)
        return final_cid

    @classmethod
    def get_trace_id(cls) -> str:
        """Retrieves active trace ID or initializes one."""
        tid = _trace_id_ctx.get()
        if not tid:
            tid = f"trace-{uuid.uuid4().hex[:16]}"
            _trace_id_ctx.set(tid)
        return tid

    @classmethod
    def set_trace_id(cls, tid: Optional[str]) -> str:
        final_tid = tid.strip() if tid and tid.strip() else f"trace-{uuid.uuid4().hex[:16]}"
        _trace_id_ctx.set(final_tid)
        return final_tid

    @classmethod
    def get_parent_span_id(cls) -> Optional[str]:
        return _parent_span_id_ctx.get()

    @classmethod
    def set_parent_span_id(cls, span_id: Optional[str]):
        _parent_span_id_ctx.set(span_id)

    @classmethod
    def get_current_span_id(cls) -> Optional[str]:
        return _current_span_id_ctx.get()

    @classmethod
    def set_current_span_id(cls, span_id: Optional[str]):
        _current_span_id_ctx.set(span_id)

    @classmethod
    def get_current_stage(cls) -> SpanStage:
        return _current_stage_ctx.get()

    @classmethod
    def set_current_stage(cls, stage: SpanStage):
        _current_stage_ctx.set(stage)

    @classmethod
    def get_client_platform(cls) -> str:
        return _client_platform_ctx.get()

    @classmethod
    def set_client_platform(cls, platform: Optional[str]):
        _client_platform_ctx.set(platform or "unknown")

    @classmethod
    def to_headers(cls) -> Dict[str, str]:
        """Constructs outbound HTTP headers for cross-service / cross-tier propagation."""
        headers = {
            cls.CORRELATION_ID_HEADER: cls.get_correlation_id(),
            cls.REQUEST_ID_HEADER: cls.get_correlation_id(),
            cls.TRACE_ID_HEADER: cls.get_trace_id(),
            cls.CLIENT_PLATFORM_HEADER: cls.get_client_platform(),
        }
        span_id = cls.get_current_span_id()
        if span_id:
            headers[cls.SPAN_ID_HEADER] = span_id
        return headers

    @classmethod
    def reset(cls):
        """Resets all context variables for test isolation or connection teardown."""
        _correlation_id_ctx.set(None)
        _trace_id_ctx.set(None)
        _parent_span_id_ctx.set(None)
        _current_span_id_ctx.set(None)
        _current_stage_ctx.set(SpanStage.API)
        _client_platform_ctx.set("unknown")
