"""REST API Endpoints for Mobile-First Health Worker Application."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from packages.types.enums import UserRole
from packages.auth.jwt import get_current_user_token, TokenPayload, require_roles
from services.health_worker.models import (
    CommunityProgram,
    BatchSyncRequest,
    BatchSyncResponse,
    ReferralCreatePayload,
    ReferralRecord,
    FollowUpCreatePayload,
    FollowUpRecord,
    HealthWorkerDashboard,
)
from services.health_worker.service import health_worker_service

router = APIRouter(prefix="/health-worker", tags=["Health Worker Mobile API"])


@router.get("/programs", response_model=List[CommunityProgram])
async def list_programs(
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN, UserRole.CLINICIAN]))
):
    """Lists registered community health and NCD screening programs."""
    return health_worker_service.list_programs()


@router.get("/dashboard", response_model=HealthWorkerDashboard)
async def get_worker_dashboard(
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN]))
):
    """Retrieves operational metrics, screening counts, and pending followups for worker."""
    return health_worker_service.get_dashboard(current_user)


@router.post("/sync", response_model=BatchSyncResponse)
async def batch_sync_drafts(
    request: BatchSyncRequest,
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN]))
):
    """Processes batch sync of offline drafts created in low-connectivity rural environments.
    Supports idempotency, automatic conflict detection and merging, and structured observation generation.
    """
    return health_worker_service.process_batch_sync(current_user, request)


@router.post("/register")
async def register_citizen_endpoint(
    payload: Dict[str, Any],
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN]))
):
    """Direct citizen registration from the mobile field app."""
    try:
        cit, was_conflict = health_worker_service.register_citizen(current_user, payload)
        return {
            "status": "CONFLICT_RESOLVED" if was_conflict else "SUCCESS",
            "citizen": cit.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/consent")
async def record_consent_endpoint(
    payload: Dict[str, Any],
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN]))
):
    """Records ABDM-compliant informed consent from the citizen."""
    try:
        consent_dir = health_worker_service.record_consent(current_user, payload)
        return {
            "status": "ACTIVE",
            "consent_id": consent_dir.id,
            "citizen_id": consent_dir.citizen_id,
            "purpose": consent_dir.purpose,
            "expires_at": consent_dir.expires_at.isoformat() if consent_dir.expires_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/screening")
async def record_screening_endpoint(
    payload: Dict[str, Any],
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN]))
):
    """Evaluates dynamic questionnaire responses and vital measurements, generating LOINC observations."""
    try:
        return health_worker_service.record_screening(current_user, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/risk-assessment/{citizen_id}")
async def generate_risk_and_action(
    citizen_id: str,
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN, UserRole.CLINICIAN]))
):
    """Generates AI risk assessment and actionable next step recommendations for frontline worker."""
    try:
        return health_worker_service.generate_risk_and_recommendation(current_user, citizen_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refer", response_model=ReferralRecord)
async def refer_citizen_endpoint(
    payload: ReferralCreatePayload,
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN]))
):
    """Issues a formal clinical referral slip to a PHC/CHC/District Hospital and enqueues triage if urgent."""
    try:
        return health_worker_service.create_referral(current_user, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/followup", response_model=FollowUpRecord)
async def schedule_followup_endpoint(
    payload: FollowUpCreatePayload,
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN]))
):
    """Schedules a home visit or community camp follow-up."""
    try:
        return health_worker_service.create_followup(current_user, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/followups", response_model=List[FollowUpRecord])
async def list_followups_endpoint(
    status: Optional[str] = None,
    current_user: TokenPayload = Depends(require_roles([UserRole.HEALTH_WORKER, UserRole.SYSTEM_ADMIN]))
):
    """Retrieves all scheduled follow-ups for the health worker."""
    return health_worker_service.list_followups(current_user, status_filter=status)
