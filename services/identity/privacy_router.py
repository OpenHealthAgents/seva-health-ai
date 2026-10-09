"""Citizen Privacy Center API Router for SevaHealth AI.

Enables citizens to:
- Grant consent across all 8 healthcare consent categories
- View active and historical consents with audit trails
- Modify consent scopes and expiration dates
- Revoke consent immediately (including revocable wearable access)
- View real-time audit ledger of who accessed what health data and why

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from packages.clinical_models.consent import (
    ConsentCategory,
    ConsentStatus,
    HealthcareConsent,
    consent_manager,
)
from packages.auth.jwt import TokenPayload, get_current_user_token
from packages.types.enums import UserRole
from services.store import store

router = APIRouter(prefix="/privacy", tags=["Citizen Privacy Center"])


class GrantConsentRequest(BaseModel):
    subject: Optional[str] = Field(None, description="Citizen ID (defaults to current logged-in citizen)")
    category: ConsentCategory = Field(description="Consent category")
    purpose: str = Field(description="Purpose of health data processing")
    scope: List[str] = Field(
        default_factory=lambda: ["vitals", "labs", "lifestyle", "risk_scores"],
        description="Data types permitted"
    )
    recipient: str = Field(default="PRIMARY_CARE_TEAM", description="Recipient entity, role, or service")
    expires_at: Optional[str] = Field(None, description="ISO-8601 expiration timestamp")
    version: str = Field(default="v1.0.0", description="Policy version")


class ModifyConsentRequest(BaseModel):
    new_scope: Optional[List[str]] = None
    new_expires_at: Optional[str] = None
    new_purpose: Optional[str] = None


class RevokeConsentRequest(BaseModel):
    reason: str = Field(default="Revoked by citizen request", description="Reason for consent revocation")


def _resolve_subject(token: TokenPayload, requested_subject: Optional[str] = None) -> str:
    """Resolves subject ensuring citizens can only manage their own consents."""
    if requested_subject and token.role in [UserRole.SYSTEM_ADMIN, UserRole.CLINICIAN]:
        return requested_subject
    if token.role == UserRole.CITIZEN:
        # Check citizen record mapping
        citizen = store.get_citizen_by_user_id(token.sub)
        return citizen.id if citizen else token.sub
    return requested_subject or token.sub


@router.post("/consents", response_model=HealthcareConsent, status_code=status.HTTP_201_CREATED)
async def grant_consent(
    payload: GrantConsentRequest,
    actor: TokenPayload = Depends(get_current_user_token),
) -> HealthcareConsent:
    """Grants a new consent directive across any of the 8 categories."""
    subject_id = _resolve_subject(actor, payload.subject)

    consent = consent_manager.grant(
        subject=subject_id,
        category=payload.category,
        purpose=payload.purpose,
        scope=payload.scope,
        recipient=payload.recipient,
        expires_at=payload.expires_at,
        version=payload.version,
        actor_id=actor.sub,
        actor_role=actor.role.value,
    )
    # Mirror into store
    store.add_consent(consent)
    return consent


@router.get("/consents", response_model=List[HealthcareConsent])
async def list_consents(
    subject: Optional[str] = None,
    category: Optional[ConsentCategory] = None,
    status_filter: Optional[ConsentStatus] = Query(None, alias="status"),
    actor: TokenPayload = Depends(get_current_user_token),
) -> List[HealthcareConsent]:
    """Lists all consents for the citizen, with optional category/status filters."""
    subject_id = _resolve_subject(actor, subject)
    return consent_manager.list_consents(
        subject=subject_id,
        category=category,
        status=status_filter,
    )


@router.get("/consents/{consent_id}", response_model=HealthcareConsent)
async def view_consent(
    consent_id: str,
    actor: TokenPayload = Depends(get_current_user_token),
) -> HealthcareConsent:
    """Views a specific consent directive including complete audit trail."""
    consent = consent_manager.view(consent_id)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent directive '{consent_id}' not found.",
        )

    # Authorization: citizens can only view their own consent
    subject_id = _resolve_subject(actor)
    if actor.role == UserRole.CITIZEN and consent.subject != subject_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view consent belonging to another citizen.",
        )

    # Log view action in audit trail
    consent.record_access(
        actor_id=actor.sub,
        actor_role=actor.role.value,
        details=f"Viewed consent details and audit history by {actor.role.value}",
        granted=True,
    )

    return consent


@router.patch("/consents/{consent_id}", response_model=HealthcareConsent)
async def modify_consent(
    consent_id: str,
    payload: ModifyConsentRequest,
    actor: TokenPayload = Depends(get_current_user_token),
) -> HealthcareConsent:
    """Modifies scope, expiration, or purpose of an active consent directive."""
    consent = consent_manager.view(consent_id)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent directive '{consent_id}' not found.",
        )

    subject_id = _resolve_subject(actor)
    if actor.role == UserRole.CITIZEN and consent.subject != subject_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify consent belonging to another citizen.",
        )

    return consent_manager.modify(
        consent_id=consent_id,
        new_scope=payload.new_scope,
        new_expires_at=payload.new_expires_at,
        new_purpose=payload.new_purpose,
        actor_id=actor.sub,
        actor_role=actor.role.value,
    )


@router.post("/consents/{consent_id}/revoke", response_model=HealthcareConsent)
async def revoke_consent(
    consent_id: str,
    payload: RevokeConsentRequest,
    actor: TokenPayload = Depends(get_current_user_token),
) -> HealthcareConsent:
    """Revokes an active consent directive immediately with audit recording."""
    consent = consent_manager.view(consent_id)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consent directive '{consent_id}' not found.",
        )

    subject_id = _resolve_subject(actor)
    if actor.role == UserRole.CITIZEN and consent.subject != subject_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke consent belonging to another citizen.",
        )

    revoked = consent_manager.revoke(
        consent_id=consent_id,
        reason=payload.reason,
        actor_id=actor.sub,
        actor_role=actor.role.value,
    )
    store.revoke_consent(consent.subject, consent_id)
    return revoked


@router.post("/wearables/revoke")
async def revoke_wearable_access(
    reason: str = "Revoked continuous wearable data stream",
    actor: TokenPayload = Depends(get_current_user_token),
) -> Dict[str, Any]:
    """Quick one-click revocation of all wearable data streams for the citizen."""
    subject_id = _resolve_subject(actor)
    wearable_consents = consent_manager.list_consents(
        subject=subject_id,
        category=ConsentCategory.WEARABLE_DATA,
        status=ConsentStatus.ACTIVE,
    )

    revoked_count = 0
    for wc in wearable_consents:
        consent_manager.revoke(
            consent_id=wc.id,
            reason=reason,
            actor_id=actor.sub,
            actor_role=actor.role.value,
        )
        store.revoke_consent(subject_id, wc.id)
        revoked_count += 1

    return {
        "status": "SUCCESS",
        "subject": subject_id,
        "wearable_access_status": "REVOKED",
        "revoked_directives_count": revoked_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Continuous wearable sync halted. No future sensor readings will be ingested without renewed consent.",
    }


@router.get("/summary")
async def get_privacy_summary(
    subject: Optional[str] = None,
    actor: TokenPayload = Depends(get_current_user_token),
) -> Dict[str, Any]:
    """Returns a high-level citizen privacy dashboard summary."""
    subject_id = _resolve_subject(actor, subject)
    all_consents = consent_manager.list_consents(subject=subject_id)

    category_summary: Dict[str, Dict[str, Any]] = {}
    for cat in ConsentCategory:
        cat_consents = [c for c in all_consents if c.category == cat]
        active = [c for c in cat_consents if c.is_valid()]
        category_summary[cat.value] = {
            "is_granted": len(active) > 0,
            "active_count": len(active),
            "total_directives": len(cat_consents),
            "latest_expires_at": active[0].expires_at if active else None,
        }

    total_audit_events = sum(len(c.audit_trail) for c in all_consents)

    return {
        "subject": subject_id,
        "total_consents": len(all_consents),
        "active_consents": sum(1 for c in all_consents if c.is_valid()),
        "categories": category_summary,
        "wearable_data_active": category_summary[ConsentCategory.WEARABLE_DATA.value]["is_granted"],
        "ai_processing_active": category_summary[ConsentCategory.AI_PROCESSING.value]["is_granted"],
        "total_audit_events_logged": total_audit_events,
        "data_protection_standard": "DISHA & ABDM Compliant (Informed, Granular, Revocable)",
    }


@router.get("/audit-trail")
async def get_privacy_audit_trail(
    subject: Optional[str] = None,
    limit: int = 50,
    actor: TokenPayload = Depends(get_current_user_token),
) -> List[Dict[str, Any]]:
    """Returns complete audit trail of all consent grants, modifications, revocations, and data accesses."""
    subject_id = _resolve_subject(actor, subject)
    all_consents = consent_manager.list_consents(subject=subject_id)

    all_events = []
    for c in all_consents:
        for ev in c.audit_trail:
            all_events.append({
                "consent_id": c.id,
                "category": c.category.value,
                "purpose": c.purpose,
                "event_id": ev.event_id,
                "timestamp": ev.timestamp,
                "action": ev.action,
                "actor_id": ev.actor_id,
                "actor_role": ev.actor_role,
                "details": ev.details,
                "recipient": ev.recipient,
            })

    # Sort descending by timestamp
    all_events.sort(key=lambda e: e["timestamp"], reverse=True)
    return all_events[:limit]
