from typing import Tuple, Optional
from fastapi import HTTPException, status
from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from services.store import store, CitizenRecord, UserRecord


class HealthcareAuthorizationEngine:
    """Enforces least privilege, tenant boundaries, care context, and consent-aware authorization.

    Standards:
    - DISHA / ABDM Healthcare Data Privacy Directives
    - Least Privilege & Need-to-Know Clinical Boundaries
    """

    @classmethod
    def can_access_citizen_record(
        cls,
        actor: TokenPayload,
        citizen: CitizenRecord,
        purpose: str = "CARE_DELIVERY"
    ) -> Tuple[bool, str]:
        # 1. Organization / Tenant Boundary Check
        # Primary tenant isolation: Users can only access records in their tenant (or state parent)
        if actor.tenant_id != citizen.tenant_id and actor.tenant_id != "karnataka_state_health":
            return False, f"Cross-tenant access prohibited. Actor tenant '{actor.tenant_id}' does not match citizen tenant '{citizen.tenant_id}'."

        # 2. Citizen Role (Self-Access Only)
        if actor.role == UserRole.CITIZEN:
            if citizen.user_id != actor.sub and citizen.id != actor.sub:
                return False, "Access denied. Citizens can only access their own medical records."
            return True, "Authorized: Citizen self-access"

        # 3. Public Health Administrator (Aggregated / De-identified Only)
        if actor.role == UserRole.PUBLIC_HEALTH_ADMIN:
            return False, "Access denied. Public Health Administrators are restricted to aggregated population intelligence and cannot view identifiable patient health records."

        # 4. Clinician Care Context & Consent
        if actor.role == UserRole.CLINICIAN:
            clinician_user: Optional[UserRecord] = store.get_user(actor.sub)

            # Check if patient is in clinician's assigned panel
            is_assigned = clinician_user and (citizen.id in clinician_user.assigned_patients)

            # Check if citizen has granted active consent directive to clinician
            grantee_ids = [actor.sub]
            if clinician_user:
                grantee_ids.extend([clinician_user.id, clinician_user.email])
            has_consent = any(store.has_active_consent(citizen.id, gid, purpose=purpose) for gid in set(grantee_ids))

            # Check if there is a pending clinical triage case for this citizen
            triage_cases = store.list_triage_cases()
            has_pending_triage = any(tc.citizen_id == citizen.id for tc in triage_cases)

            if is_assigned or has_consent or has_pending_triage:
                return True, "Authorized: Clinician assigned to care context, triage case, or active patient consent"
            return False, "Access denied. Clinician is not assigned to this patient's care context and no active consent directive exists."

        # 5. Health Worker Jurisdiction & Program Scope
        if actor.role == UserRole.HEALTH_WORKER:
            hw_user: Optional[UserRecord] = store.get_user(actor.sub)

            hw_jurisdiction = hw_user.assigned_jurisdiction if hw_user else "All"

            # Check ward/village matching
            in_jurisdiction = (
                hw_jurisdiction == "All" or
                hw_jurisdiction in citizen.village_or_ward or
                hw_jurisdiction in citizen.district
            )

            # Check active consent
            grantee_ids = [actor.sub]
            if hw_user:
                grantee_ids.extend([hw_user.id, hw_user.email])
            has_consent = any(store.has_active_consent(citizen.id, gid, purpose=purpose) for gid in set(grantee_ids))

            if in_jurisdiction or has_consent:
                return True, "Authorized: Health Worker in authorized program jurisdiction"
            return False, f"Access denied. Citizen location '{citizen.village_or_ward}' is outside Health Worker assigned jurisdiction '{hw_jurisdiction}'."

        # 6. System Administrator
        if actor.role == UserRole.SYSTEM_ADMIN:
            return True, "Authorized: System Administrator maintenance"

        return False, "Access denied: Role not permitted"

    @classmethod
    def enforce_citizen_access(
        cls,
        actor: TokenPayload,
        citizen: CitizenRecord,
        purpose: str = "CARE_DELIVERY"
    ):
        allowed, reason = cls.can_access_citizen_record(actor, citizen, purpose=purpose)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=reason,
            )
