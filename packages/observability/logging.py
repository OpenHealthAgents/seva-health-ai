"""Safe Structured Logging Configuration for SevaHealth AI.

Combines Structlog with HealthcareLogSanitizer and CorrelationContext to guarantee:
1. Every application log includes correlation_id and trace_id.
2. Clinical data is strictly scrubbed before hitting console or streams.
"""

import sys
import logging
from typing import Any, Dict
import structlog

from packages.observability.context import CorrelationContext
from packages.observability.sanitizer import HealthcareLogSanitizer


def _inject_correlation_context(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Injects current correlation ID, trace ID, and stage into every structured log entry."""
    event_dict["correlation_id"] = CorrelationContext.get_correlation_id()
    event_dict["trace_id"] = CorrelationContext.get_trace_id()
    event_dict["stage"] = CorrelationContext.get_current_stage().value
    event_dict["platform"] = CorrelationContext.get_client_platform()
    return event_dict


# Configure Structlog processors pipeline
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _inject_correlation_context,
        HealthcareLogSanitizer.scrub_structlog_event,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


def get_safe_logger(name: str = "sevahealth"):
    """Returns a clinical-safe structured logger bound with the given module name."""
    return structlog.get_logger(name)
