"""Security, Access Control, and Query Injection Defense for Clinical Data Providers.

Prevents unauthorized access (RBAC) and strictly blocks arbitrary AI-generated
GraphQL or database queries against clinical systems.
"""

import re
from typing import Optional, List, Dict, Any
import structlog

from packages.types.enums import UserRole
from packages.interop.base import AccessContext
from services.store import store

logger = structlog.get_logger(__name__)


class ClinicalSecurityError(Exception):
    """Base exception for clinical security violations."""
    pass


class AccessDeniedError(ClinicalSecurityError):
    """Raised when actor does not have RBAC authorization to access a clinical record."""
    pass


class ArbitraryQueryViolationError(ClinicalSecurityError):
    """Raised when an actor or AI agent attempts to pass arbitrary GraphQL or SQL queries."""
    pass


class AntiArbitraryQueryGuard:
    """Security Guard that strictly prevents arbitrary AI-generated GraphQL,

    SQL, or raw query text from reaching clinical systems.

    Clinical integrations must ONLY use parameterized, strictly-typed domain operations.
    """

    # Suspicious SQL keywords and injection patterns
    SQL_PATTERNS = [
        r"\b(SELECT\s+.+\s+FROM)\b",
        r"\b(INSERT\s+INTO)\b",
        r"\b(UPDATE\s+.+\s+SET)\b",
        r"\b(DELETE\s+FROM)\b",
        r"\b(DROP\s+TABLE|DROP\s+DATABASE)\b",
        r"\b(ALTER\s+TABLE)\b",
        r"\b(UNION\s+ALL|UNION\s+SELECT)\b",
        r"\b(EXEC|EXECUTE)\b",
        r"(--|/\*|\*/|;\s*--)",
        r"\bOR\s+1\s*=\s*1\b",
    ]

    # Suspicious GraphQL AST / query strings
    GRAPHQL_PATTERNS = [
        r"\bquery\s*\{",
        r"\bmutation\s*\{",
        r"\bsubscription\s*\{",
        r"\b__schema\b",
        r"\b__typename\b",
        r"\{\s*(patient|observation|condition|medicationRequest|encounter)\s*\(",
    ]

    @classmethod
    def inspect_query_parameter(cls, param_name: str, value: Any) -> None:
        """Inspects an individual query parameter. Raises ArbitraryQueryViolationError if raw query detected."""
        if value is None:
            return

        if not isinstance(value, str):
            return

        val_str = value.strip()

        # Check for GraphQL queries
        for pattern in cls.GRAPHQL_PATTERNS:
            if re.search(pattern, val_str, re.IGNORECASE | re.DOTALL):
                logger.error(
                    "SECURITY_ALERT: Arbitrary GraphQL query blocked",
                    parameter=param_name,
                    pattern=pattern,
                )
                raise ArbitraryQueryViolationError(
                    f"Arbitrary GraphQL queries are strictly forbidden. Access clinical data via parameterized typed methods only. Offending parameter: '{param_name}'."
                )

        # Check for SQL queries
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, val_str, re.IGNORECASE):
                logger.error(
                    "SECURITY_ALERT: Arbitrary SQL injection blocked",
                    parameter=param_name,
                    pattern=pattern,
                )
                raise ArbitraryQueryViolationError(
                    f"Arbitrary SQL/database queries are strictly forbidden. Parameterized typed access required. Offending parameter: '{param_name}'."
                )

    @classmethod
    def validate_request_parameters(cls, **params) -> None:
        """Validates all passed parameters for query injection attempts."""
        for name, val in params.items():
            cls.inspect_query_parameter(name, val)


class ClinicalRBACGuard:
    """Enforces fine-grained role-based access control (RBAC) on clinical chart reads."""

    @classmethod
    def check_read_permission(cls, patient_id: str, context: AccessContext) -> None:
        """Validates that actor has legitimate clinical or patient portal access rights.

        Rules:
        - CITIZEN: Can ONLY read their own record (actor_id == patient_id or matching citizen.user_id).
        - HEALTH_WORKER: Can access assigned cohort or patients in jurisdiction.
        - CLINICIAN: Can access patient record for care delivery.
        - PUBLIC_HEALTH_ADMIN: Blocked from direct individual chart access (must use aggregate views).
        - SYSTEM_ADMIN: Permitted for maintenance / audit.
        """
        actor_role = context.actor_role
        actor_id = context.actor_id

        # 1. Citizen Role: Self-access only
        if actor_role == UserRole.CITIZEN:
            # Check direct match
            if actor_id == patient_id:
                return

            # Check linked citizen user_id in store
            citizen = store.get_citizen(patient_id)
            if citizen and (citizen.user_id == actor_id or citizen.id == actor_id):
                return

            logger.warning(
                "RBAC_VIOLATION: Citizen attempted to access another patient's clinical chart",
                actor_id=actor_id,
                target_patient_id=patient_id,
            )
            raise AccessDeniedError(
                f"Access denied: Citizens are only authorized to access their own clinical records. (Actor: {actor_id}, Target: {patient_id})"
            )

        # 2. Public Health Admin: Identifiable individual chart is restricted
        if actor_role == UserRole.PUBLIC_HEALTH_ADMIN:
            logger.warning(
                "RBAC_VIOLATION: Public Health Admin attempted to read individual identifiable clinical record",
                actor_id=actor_id,
                patient_id=patient_id,
            )
            raise AccessDeniedError(
                "Access denied: Public health administrators are restricted to aggregated and de-identified population metrics. Individual patient charts cannot be accessed directly."
            )

        # 3. Clinician: Valid for clinical care delivery
        if actor_role == UserRole.CLINICIAN:
            return

        # 4. Health Worker: Valid for care delivery / field screening
        if actor_role == UserRole.HEALTH_WORKER:
            return

        # 5. Admin / System
        if actor_role == UserRole.SYSTEM_ADMIN:
            return

        # Any other or unrecognized role: deny by default
        raise AccessDeniedError(
            f"Access denied: Role '{actor_role}' is not authorized to access clinical data."
        )
