"""Audit Trail Recorder for SevaHealth AI.

Tracks auditable actions across citizens, clinicians, and administrative actors.
Integrates correlation tracking, metrics recording, and automatic PHI sanitization.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid

from packages.types.enums import AuditAction, UserRole
from packages.observability.context import CorrelationContext
from packages.observability.sanitizer import HealthcareLogSanitizer
from packages.observability.metrics import metrics


class AuditRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    actor_id: str
    actor_role: UserRole
    action: AuditAction
    resource_type: str
    resource_id: str
    correlation_id: str = Field(default_factory=lambda: CorrelationContext.get_correlation_id())
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogger:
    """In-memory audit log recorder with database persistence hooks and metric emissions."""

    def __init__(self):
        self._records: list[AuditRecord] = []

    def record(
        self,
        tenant_id: str,
        actor_id: str,
        actor_role: UserRole,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> AuditRecord:
        clean_details = HealthcareLogSanitizer.sanitize_data(details or {})
        corr_id = correlation_id or CorrelationContext.get_correlation_id()

        record = AuditRecord(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=corr_id,
            details=clean_details if isinstance(clean_details, dict) else {},
            ip_address=ip_address,
        )
        self._records.append(record)

        # Record operational metric
        metrics.record_audit(
            action=action.value if hasattr(action, "value") else str(action),
            actor_role=actor_role.value if hasattr(actor_role, "value") else str(actor_role),
            resource_type=resource_type,
        )
        return record

    def list_records(
        self,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        records = self._records
        if tenant_id:
            records = [r for r in records if r.tenant_id == tenant_id]
        if correlation_id:
            records = [r for r in records if r.correlation_id == correlation_id]
        return records[-limit:]


audit_logger = AuditLogger()
