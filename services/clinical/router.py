from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from pydantic import BaseModel

from packages.clinical_models.triage import ClinicalTriageCase
from packages.types.enums import ClinicianReviewStatus, UserRole, AuditAction
from packages.auth.jwt import get_current_user_token, TokenPayload, require_roles
from packages.observability.audit import audit_logger
from services.store import store
from services.clinical.copilot import (
    ClinicianCopilotEngine,
    ClinicianCopilotPatientView,
    AICopilotSynthesis,
    ClinicianActionPayload,
    ClinicianVerificationRecord,
)

router = APIRouter(prefix="/clinician", tags=["Clinical Decision Support & Copilot"])


class ClinicianReviewPayload(BaseModel):
    status: ClinicianReviewStatus     # APPROVED | MODIFIED | REFERRED
    review_notes: str
    updated_care_plan_instructions: Optional[str] = None


@router.get("/triage", response_model=List[ClinicalTriageCase])
async def list_triage_queue(
    status: Optional[ClinicianReviewStatus] = None,
    current_user: TokenPayload = Depends(require_roles([UserRole.CLINICIAN, UserRole.SYSTEM_ADMIN])),
):
    """Retrieves all high-risk and deteriorating cases enqueued for clinician review."""
    return store.list_triage_cases(status=status)


@router.post("/review/{triage_id}", response_model=ClinicalTriageCase)
async def submit_clinical_review(
    triage_id: str,
    payload: ClinicianReviewPayload,
    current_user: TokenPayload = Depends(require_roles([UserRole.CLINICIAN, UserRole.SYSTEM_ADMIN])),
):
    case = store.triage_cases.get(triage_id)
    if not case:
        raise HTTPException(status_code=404, detail="Triage case not found")

    case.status = payload.status
    case.assigned_clinician_id = current_user.sub
    case.review_notes = payload.review_notes
    case.reviewed_at = datetime.now(timezone.utc)

    # Mark associated care plan as reviewed
    plan = store.get_care_plan(case.citizen_id)
    if plan:
        plan.clinician_reviewed = True
        plan.clinician_id = current_user.sub
        if payload.updated_care_plan_instructions:
            plan.nutrition_guidance += f" [Doctor Note: {payload.updated_care_plan_instructions}]"
        store.set_care_plan(plan)

    audit_logger.record(
        tenant_id=case.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.CLINICIAN_REVIEWED,
        resource_type="ClinicalTriageCase",
        resource_id=case.id,
        details={"status": payload.status.value, "notes": payload.review_notes},
    )

    return case


# --- CLINICIAN AI COPILOT ENDPOINTS ---

@router.get("/copilot/patient-summary/{citizen_id}", response_model=ClinicianCopilotPatientView)
async def get_patient_summary(
    citizen_id: str,
    current_user: TokenPayload = Depends(require_roles([UserRole.CLINICIAN, UserRole.SYSTEM_ADMIN])),
):
    """Assembles all 11 patient dimensions into a consolidated view for the attending clinician:

    Current risks, Risk trajectory, Recent vitals, Recent labs, Wearable trends,
    Lifestyle, Medications, Adherence, Interventions, Alerts, Documents.
    """
    try:
        view = ClinicianCopilotEngine.assemble_patient_summary(citizen_id, current_user)
        return view
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to assemble patient summary: {str(exc)}")


@router.post("/copilot/generate/{citizen_id}", response_model=AICopilotSynthesis)
async def generate_copilot_synthesis(
    citizen_id: str,
    current_user: TokenPayload = Depends(require_roles([UserRole.CLINICIAN, UserRole.SYSTEM_ADMIN])),
):
    """Generates 7 AI decision-support sections clearly marked as AI-GENERATED:

    1. Clinical summary
    2. Risk summary
    3. Recent changes
    4. Missing information
    5. Possible contributing factors
    6. Suggested follow-up
    7. Questions for clinician consideration

    NOTE: Never automatically written into the legal clinical record without explicit clinician confirmation.
    """
    try:
        synthesis = ClinicianCopilotEngine.generate_copilot_synthesis(citizen_id, current_user)
        return synthesis
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate copilot synthesis: {str(exc)}")


@router.post("/copilot/action/{citizen_id}", response_model=ClinicianVerificationRecord)
async def submit_clinician_action(
    citizen_id: str,
    payload: ClinicianActionPayload,
    current_user: TokenPayload = Depends(require_roles([UserRole.CLINICIAN, UserRole.SYSTEM_ADMIN])),
):
    """Processes explicit clinician decision actions:

    - ACCEPT: Confirms AI draft and stamps into permanent legal record as CLINICIAN-VERIFIED.
    - EDIT: Modifies summary/plan and stamps into permanent legal record.
    - REJECT: Rejects draft with rationale; NEVER written to legal clinical record.
    - ADD_COMMENT: Attaches clinical observation notes.
    - CREATE_CARE_PLAN: Prescribes new or modified 30-day care plan.
    - REFER: Issues clinical referral to higher facility/specialist.
    - ESCALATE: Triggers urgent/emergency escalation alert.
    """
    try:
        record = ClinicianCopilotEngine.process_clinician_action(citizen_id, payload, current_user)
        return record
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process clinician action: {str(exc)}")


@router.get("/copilot/legal-record/{citizen_id}")
async def get_legal_clinical_records(
    citizen_id: str,
    current_user: TokenPayload = Depends(require_roles([UserRole.CLINICIAN, UserRole.SYSTEM_ADMIN])),
):
    """Retrieves only verified, stamped, legal clinical encounter records.

    Unverified AI suggestions and rejected drafts are strictly excluded.
    """
    records = store.get_legal_clinical_records(citizen_id)
    return {
        "citizen_id": citizen_id,
        "total_records": len(records),
        "records": records,
        "governance_rule": "Strict Clinical Governance: AI conclusions are only recorded upon explicit clinician verification.",
    }
