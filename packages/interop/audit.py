"""Audit Logging for Clinical Data Provider Interoperability Access."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid
import structlog

from packages.types.enums import UserRole
from packages.interop.models import ClinicalSourceSystem
from packages.interop.base import AccessContext
from services.store import store

logger = structlog.get_logger(__name__)


class ClinicalAccessAuditLogger:
    """Immutable audit trail of all clinical data reads across all federated EMR systems."""

    @classmethod
    def log_access(
        cls,
        context: AccessContext,
        patient_id: str,
        source_system: str,
        resource_type: str,
        items_count: int,
        status: str = "GRANTED",
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Records an access event into the audit trail."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        audit_entry = {
            "event_id": event_id,
            "timestamp": timestamp,
            "actor_id": context.actor_id,
            "actor_role": context.actor_role.value if hasattr(context.actor_role, "value") else str(context.actor_role),
            "is_ai_agent": context.is_ai_agent,
            "patient_id": patient_id,
            "source_system": source_system,
            "resource_type": resource_type,
            "items_count": items_count,
            "purpose_of_use": context.purpose_of_use,
            "request_id": context.request_id,
            "tenant_id": context.tenant_id,
            "status": status,
            "error_message": error_message,
            "details": details or {},
        }

        # Store in centralized store
        store.add_clinical_access_audit_log(audit_entry)

        # Emit structured log
        logger.info(
            "CLINICAL_ACCESS_AUDIT",
            event_id=event_id,
            actor_id=context.actor_id,
            role=context.actor_role,
            is_ai_agent=context.is_ai_agent,
            patient_id=patient_id,
            source=source_system,
            resource=resource_type,
            count=items_count,
            status=status,
        )

        return audit_entry

    @classmethod
    def get_audit_trail(
        cls,
        patient_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieves recent clinical access logs."""
        return store.get_clinical_access_audit_logs(
            patient_id=patient_id,
            actor_id=actor_id,
            limit=limit,
        )
