from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid

from packages.types.enums import AuditAction, UserRole


class AuditRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    actor_id: str
    actor_role: UserRole
    action: AuditAction
    resource_type: str
    resource_id: str
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogger:
    """In-memory audit log recorder with database persistence hooks."""

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
    ) -> AuditRecord:
        record = AuditRecord(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        self._records.append(record)
        return record

    def list_records(self, tenant_id: Optional[str] = None, limit: int = 100) -> list[AuditRecord]:
        if tenant_id:
            filtered = [r for r in self._records if r.tenant_id == tenant_id]
            return filtered[-limit:]
        return self._records[-limit:]


audit_logger = AuditLogger()
