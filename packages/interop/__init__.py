"""SevaHealth Clinical Interoperability and Multi-EMR Abstraction Package.

Provides a unified, secure ClinicalDataProvider abstraction bridging:
- SevaHealth local clinical repository
- openEHR / EHRbase
- bezs-emr-gql (FHIR R4)
- bezs-hms (Intake & Consultation SOAP notes/orders)

Enforces zero provider model leakage, anti-arbitrary query defense, RBAC,
and immutable clinical access audit logging.
"""

from packages.interop.models import (
    ClinicalSourceSystem,
    ObservationCategory,
    ConditionClinicalStatus,
    ConditionVerificationStatus,
    MedicationStatus,
    EncounterClass,
    CarePlanStatus,
    ClinicalDocumentType,
    NormalizedPatient,
    NormalizedObservation,
    NormalizedCondition,
    NormalizedMedication,
    NormalizedEncounter,
    NormalizedCarePlan,
    NormalizedClinicalDocument,
    FederatedClinicalChart,
)
from packages.interop.base import (
    AccessContext,
    ClinicalDataProvider,
)
from packages.interop.security import (
    ClinicalRBACGuard,
    AntiArbitraryQueryGuard,
    ClinicalSecurityError,
    AccessDeniedError,
    ArbitraryQueryViolationError,
)
from packages.interop.audit import ClinicalAccessAuditLogger
from packages.interop.adapters.local_adapter import SevaHealthLocalAdapter
from packages.interop.adapters.openehr_adapter import OpenEhrEhrBaseAdapter
from packages.interop.adapters.emr_gql_adapter import EmrGqlAdapter
from packages.interop.adapters.hms_adapter import HmsAdapter
from packages.interop.service import (
    FederatedClinicalDataProvider,
    federated_clinical_data_provider,
)

__all__ = [
    "ClinicalSourceSystem",
    "ObservationCategory",
    "ConditionClinicalStatus",
    "ConditionVerificationStatus",
    "MedicationStatus",
    "EncounterClass",
    "CarePlanStatus",
    "ClinicalDocumentType",
    "NormalizedPatient",
    "NormalizedObservation",
    "NormalizedCondition",
    "NormalizedMedication",
    "NormalizedEncounter",
    "NormalizedCarePlan",
    "NormalizedClinicalDocument",
    "FederatedClinicalChart",
    "AccessContext",
    "ClinicalDataProvider",
    "ClinicalRBACGuard",
    "AntiArbitraryQueryGuard",
    "ClinicalSecurityError",
    "AccessDeniedError",
    "ArbitraryQueryViolationError",
    "ClinicalAccessAuditLogger",
    "SevaHealthLocalAdapter",
    "OpenEhrEhrBaseAdapter",
    "EmrGqlAdapter",
    "HmsAdapter",
    "FederatedClinicalDataProvider",
    "federated_clinical_data_provider",
]
