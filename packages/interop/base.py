"""Base Abstraction for Clinical Data Providers and Interoperability Adapters."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field

from packages.types.enums import UserRole
from packages.interop.models import (
    ClinicalSourceSystem,
    NormalizedPatient,
    NormalizedObservation,
    NormalizedCondition,
    NormalizedMedication,
    NormalizedEncounter,
    NormalizedCarePlan,
    NormalizedClinicalDocument,
    ObservationCategory,
)


class AccessContext(BaseModel):
    """Forensic and authorization context for all clinical data requests.
    Every read/query must carry valid user identity and purpose of use.
    """
    actor_id: str = Field(description="Unique identifier of user/agent making the call")
    actor_role: UserRole = Field(description="Role of the actor: CITIZEN, HEALTH_WORKER, CLINICIAN, etc.")
    tenant_id: str = Field(default="karnataka_state_health", description="Tenant jurisdiction")
    purpose_of_use: str = Field(default="CARE_DELIVERY", description="CARE_DELIVERY, PATIENT_PORTAL, EMERGENCY, etc.")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_ip: Optional[str] = None
    is_ai_agent: bool = Field(default=False, description="True if request originates from AI agent runtime")


class ClinicalDataProvider(ABC):
    """Abstract Base Class for EMR and Clinical Data Adapters.

    Contract guarantees:
    1. Returns ONLY normalized internal clinical models.
    2. Completely encapsulates provider protocols (FHIR R4, openEHR AQL, Prisma HMS).
    3. Requires explicit AccessContext for permission enforcement and audit logging.
    4. Never accepts raw arbitrary query strings.
    """

    @property
    @abstractmethod
    def source_system(self) -> ClinicalSourceSystem:
        """The source system identifier represented by this provider."""
        pass

    @abstractmethod
    async def get_patient(self, patient_id: str, context: AccessContext) -> Optional[NormalizedPatient]:
        """Fetch patient demographics normalized to NormalizedPatient."""
        pass

    @abstractmethod
    async def get_observations(
        self,
        patient_id: str,
        context: AccessContext,
        category: Optional[ObservationCategory] = None,
    ) -> List[NormalizedObservation]:
        """Fetch clinical observations (vitals, labs, biomarkers) normalized to NormalizedObservation."""
        pass

    @abstractmethod
    async def get_conditions(self, patient_id: str, context: AccessContext) -> List[NormalizedCondition]:
        """Fetch active and historical medical conditions/diagnoses normalized to NormalizedCondition."""
        pass

    @abstractmethod
    async def get_medications(self, patient_id: str, context: AccessContext) -> List[NormalizedMedication]:
        """Fetch prescribed medications and active therapies normalized to NormalizedMedication."""
        pass

    @abstractmethod
    async def get_encounters(self, patient_id: str, context: AccessContext) -> List[NormalizedEncounter]:
        """Fetch clinical encounters and consultation notes normalized to NormalizedEncounter."""
        pass

    @abstractmethod
    async def get_care_plans(self, patient_id: str, context: AccessContext) -> List[NormalizedCarePlan]:
        """Fetch preventive and therapeutic care plans normalized to NormalizedCarePlan."""
        pass

    @abstractmethod
    async def get_clinical_documents(
        self, patient_id: str, context: AccessContext
    ) -> List[NormalizedClinicalDocument]:
        """Fetch structured clinical reports and documents normalized to NormalizedClinicalDocument."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Provider connectivity and liveness diagnostic check."""
        pass
