from enum import Enum


class UserRole(str, Enum):
    """Platform Role-Based Access Control Taxonomy (adapted from bezs-iam)."""
    CITIZEN = "CITIZEN"
    HEALTH_WORKER = "HEALTH_WORKER"
    CLINICIAN = "CLINICIAN"
    PUBLIC_HEALTH_ADMIN = "PUBLIC_HEALTH_ADMIN"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class RiskTier(str, Enum):
    """Composite and domain risk tier classification."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TrajectoryTrend(str, Enum):
    """Longitudinal progression trajectory."""
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DETERIORATING = "DETERIORATING"


class TriageUrgency(str, Enum):
    """Urgency level for clinician triage routing."""
    ROUTINE = "ROUTINE"       # Within 30-90 days
    PRIORITY = "PRIORITY"     # Within 14 days
    URGENT = "URGENT"         # Within 48 hours
    EMERGENT = "EMERGENT"     # Immediate same-day evaluation


class ClinicianReviewStatus(str, Enum):
    """Human-in-the-loop clinical review state machine."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    MODIFIED = "MODIFIED"
    REFERRED = "REFERRED"


class InterventionPillar(str, Enum):
    """Lifestyle medicine pillars for preventive care."""
    NUTRITION = "NUTRITION"
    PHYSICAL_ACTIVITY = "PHYSICAL_ACTIVITY"
    SLEEP_HYGIENE = "SLEEP_HYGIENE"
    STRESS_AND_LIFESTYLE = "STRESS_AND_LIFESTYLE"


class AuditAction(str, Enum):
    """Audit action types (adapted from bezs-observability)."""
    USER_REGISTERED = "USER_REGISTERED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGOUT = "LOGOUT"
    PASSWORD_RESET = "PASSWORD_RESET"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    ACCESS_DENIED = "ACCESS_DENIED"
    SCREENING_SUBMITTED = "SCREENING_SUBMITTED"
    RISK_ASSESSED = "RISK_ASSESSED"
    CARE_PLAN_GENERATED = "CARE_PLAN_GENERATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    WEARABLE_SYNCED = "WEARABLE_SYNCED"
    CLINICIAN_REVIEWED = "CLINICIAN_REVIEWED"
    DATA_EXPORTED = "DATA_EXPORTED"
    REFERRAL_ISSUED = "REFERRAL_ISSUED"
    FOLLOWUP_SCHEDULED = "FOLLOWUP_SCHEDULED"

