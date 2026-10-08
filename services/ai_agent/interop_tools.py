"""Controlled AI Agent Tools for Federated Clinical Data Providers.

Rules:
1. AI agents must access clinical information through controlled tools/services.
2. Every tool call enforces actor authorization and RBAC.
3. Every clinical data read is immutably audit-logged.
4. Arbitrary AI-generated GraphQL or SQL database queries are strictly rejected.
"""

from typing import Dict, Any, List, Optional
import structlog

from packages.auth.jwt import TokenPayload
from packages.types.enums import UserRole
from packages.interop.base import AccessContext
from packages.interop.models import (
    ObservationCategory,
    FederatedClinicalChart,
)
from packages.interop.service import federated_clinical_data_provider
from packages.interop.security import AntiArbitraryQueryGuard, ArbitraryQueryViolationError
from services.ai_agent.tools import agent_telemetry

logger = structlog.get_logger(__name__)


def _build_agent_access_context(actor: TokenPayload, purpose: str = "CARE_DELIVERY") -> AccessContext:
    """Builds authorized access context for an AI agent tool invocation."""
    role = actor.role if isinstance(actor.role, UserRole) else UserRole(str(actor.role))
    return AccessContext(
        actor_id=actor.sub,
        actor_role=role,
        tenant_id=actor.tenant_id,
        purpose_of_use=purpose,
        is_ai_agent=True,
    )


async def tool_get_federated_patient(
    patient_id: str,
    actor: TokenPayload,
    purpose: str = "CARE_DELIVERY",
) -> Dict[str, Any]:
    """Retrieves normalized master patient demographics across federated clinical repositories."""
    AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)
    ctx = _build_agent_access_context(actor, purpose)

    try:
        patient = await federated_clinical_data_provider.get_patient(patient_id, ctx)
        result = patient.model_dump() if patient else None

        agent_telemetry.log_tool_call(
            tool_name="get_federated_patient",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="SUCCESS" if patient else "NOT_FOUND",
        )
        return {"status": "SUCCESS", "patient": result}
    except Exception as e:
        agent_telemetry.log_tool_call(
            tool_name="get_federated_patient",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="ERROR",
            details=str(e),
        )
        raise


async def tool_get_federated_vitals_and_labs(
    patient_id: str,
    actor: TokenPayload,
    category: Optional[str] = None,
    purpose: str = "CARE_DELIVERY",
) -> Dict[str, Any]:
    """Retrieves federated vitals and laboratory observations normalized across all sources."""
    AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id, category=category)
    ctx = _build_agent_access_context(actor, purpose)

    cat_enum = None
    if category:
        cat_upper = category.upper()
        if "VITAL" in cat_upper:
            cat_enum = ObservationCategory.VITAL_SIGN
        elif "LAB" in cat_upper:
            cat_enum = ObservationCategory.LABORATORY

    try:
        observations = await federated_clinical_data_provider.get_observations(patient_id, ctx, category=cat_enum)
        agent_telemetry.log_tool_call(
            tool_name="get_federated_vitals_and_labs",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id, "category": category},
            status="SUCCESS",
        )
        return {
            "status": "SUCCESS",
            "count": len(observations),
            "observations": [o.model_dump() for o in observations],
        }
    except Exception as e:
        agent_telemetry.log_tool_call(
            tool_name="get_federated_vitals_and_labs",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id, "category": category},
            status="ERROR",
            details=str(e),
        )
        raise


async def tool_get_federated_conditions(
    patient_id: str,
    actor: TokenPayload,
    purpose: str = "CARE_DELIVERY",
) -> Dict[str, Any]:
    """Retrieves active medical conditions and clinical diagnoses across federated sources."""
    AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)
    ctx = _build_agent_access_context(actor, purpose)

    try:
        conditions = await federated_clinical_data_provider.get_conditions(patient_id, ctx)
        agent_telemetry.log_tool_call(
            tool_name="get_federated_conditions",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="SUCCESS",
        )
        return {
            "status": "SUCCESS",
            "count": len(conditions),
            "conditions": [c.model_dump() for c in conditions],
        }
    except Exception as e:
        agent_telemetry.log_tool_call(
            tool_name="get_federated_conditions",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="ERROR",
            details=str(e),
        )
        raise


async def tool_get_federated_medications(
    patient_id: str,
    actor: TokenPayload,
    purpose: str = "CARE_DELIVERY",
) -> Dict[str, Any]:
    """Retrieves prescribed medications and therapies across federated systems."""
    AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)
    ctx = _build_agent_access_context(actor, purpose)

    try:
        medications = await federated_clinical_data_provider.get_medications(patient_id, ctx)
        agent_telemetry.log_tool_call(
            tool_name="get_federated_medications",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="SUCCESS",
        )
        return {
            "status": "SUCCESS",
            "count": len(medications),
            "medications": [m.model_dump() for m in medications],
        }
    except Exception as e:
        agent_telemetry.log_tool_call(
            tool_name="get_federated_medications",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="ERROR",
            details=str(e),
        )
        raise


async def tool_get_federated_encounters(
    patient_id: str,
    actor: TokenPayload,
    purpose: str = "CARE_DELIVERY",
) -> Dict[str, Any]:
    """Retrieves physical, field, and virtual video consultations across federated systems."""
    AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)
    ctx = _build_agent_access_context(actor, purpose)

    try:
        encounters = await federated_clinical_data_provider.get_encounters(patient_id, ctx)
        agent_telemetry.log_tool_call(
            tool_name="get_federated_encounters",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="SUCCESS",
        )
        return {
            "status": "SUCCESS",
            "count": len(encounters),
            "encounters": [e.model_dump() for e in encounters],
        }
    except Exception as e:
        agent_telemetry.log_tool_call(
            tool_name="get_federated_encounters",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="ERROR",
            details=str(e),
        )
        raise


async def tool_get_federated_clinical_chart(
    patient_id: str,
    actor: TokenPayload,
    purpose: str = "CARE_DELIVERY",
) -> Dict[str, Any]:
    """Retrieves the unified longitudinal clinical chart for a patient across all EMR sources."""
    AntiArbitraryQueryGuard.validate_request_parameters(patient_id=patient_id)
    ctx = _build_agent_access_context(actor, purpose)

    try:
        chart = await federated_clinical_data_provider.get_federated_chart(patient_id, ctx)
        agent_telemetry.log_tool_call(
            tool_name="get_federated_clinical_chart",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="SUCCESS",
        )
        return {
            "status": "SUCCESS",
            "chart": chart.model_dump(),
        }
    except Exception as e:
        agent_telemetry.log_tool_call(
            tool_name="get_federated_clinical_chart",
            citizen_id=patient_id,
            actor_id=actor.sub,
            actor_role=str(actor.role),
            arguments={"patient_id": patient_id},
            status="ERROR",
            details=str(e),
        )
        raise
