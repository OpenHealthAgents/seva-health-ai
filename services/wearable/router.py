from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel

from packages.auth.jwt import get_current_user_token, TokenPayload
from packages.types.enums import AuditAction, UserRole
from packages.observability.audit import audit_logger
from services.wearable.models import (
    WearableProvider,
    WearableMetricType,
    WearableConnectionState,
    WearableProjection,
    WebhookPayload,
)
from services.wearable.adapter import wearable_adapter, MockWearableProvider
from services.store import store
from packages.clinical_models.consent import ConsentCategory, ConsentStatus, consent_manager
from packages.observability.metrics import metrics

router = APIRouter(prefix="/wearables", tags=["Wearable & Health-Data Ingestion Layer"])


class ConnectProviderRequest(BaseModel):
    citizen_id: str
    access_token: str = "demo_oauth_token_12345"
    refresh_token: Optional[str] = None
    scope: List[str] = ["activity", "heartrate", "sleep", "respiratory"]


class IncrementalSyncRequest(BaseModel):
    cursor: Optional[str] = None


@router.post("/connect/{provider}", response_model=WearableConnectionState)
async def connect_wearable_provider(
    provider: WearableProvider,
    payload: ConnectProviderRequest,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Establishes authenticated connection with an Open Wearables data provider."""
    state = await wearable_adapter.connect_provider(
        citizen_id=payload.citizen_id,
        provider=provider,
        auth_payload={"access_token": payload.access_token},
    )

    audit_logger.record(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.DATA_EXPORTED,
        resource_type="WearableConnection",
        resource_id=state.id,
        details={"provider": provider.value, "citizen_id": payload.citizen_id}
    )
    return state


@router.post("/sync/{citizen_id}")
async def sync_wearable_data(
    citizen_id: str,
    provider: Optional[WearableProvider] = Query(WearableProvider.GARMIN),
    trend: str = Query("DEFAULT"),  # DEFAULT | DETERIORATING | IMPROVING
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Performs full sync across connected Open Wearables providers."""
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    # Verify revocable WEARABLE_DATA consent
    wearable_consents = consent_manager.list_consents(subject=citizen_id, category=ConsentCategory.WEARABLE_DATA)
    if any(c.status == ConsentStatus.REVOKED for c in wearable_consents) or (wearable_consents and all(not c.is_valid() for c in wearable_consents)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wearable access has been REVOKED by citizen in the Citizen Privacy Center.",
        )

    records = await wearable_adapter.sync(
        citizen_id=citizen_id,
        provider=provider,
        physiological_trend=trend,
    )

    projection = wearable_adapter.get_projection(citizen_id)

    audit_logger.record(
        tenant_id=citizen.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.WEARABLE_SYNCED,
        resource_type="WearableTimeseries",
        resource_id=citizen_id,
        details={
            "provider": provider.value if provider else "all",
            "synced_records": len(records),
            "avg_rhr": projection.avg_resting_heart_rate if projection else None,
            "chronic_sleep_deficit": projection.chronic_sleep_deficit if projection else None,
        },
    )

    metrics.record_wearable_sync(
        device_type=provider.value if provider else "GARMIN",
        records_count=len(records),
        duration_ms=22.4,
        success=True,
    )

    proj_dump = projection.model_dump() if projection else None
    return {
        "status": "SUCCESS",
        "provider": provider.value if provider else "all",
        "synced_records_count": len(records),
        "projection": proj_dump,
        "seven_day_baselines": proj_dump,
        "sample_records": [r.model_dump() for r in records[:5]],
    }


@router.post("/backfill-async/{citizen_id}", status_code=status.HTTP_202_ACCEPTED)
async def backfill_wearable_data_async(
    citizen_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to backfill"),
    provider: Optional[WearableProvider] = Query(WearableProvider.GARMIN),
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Enqueues large multi-day timeseries telemetry backfill to background queue without blocking citizen UX."""
    from packages.queue.manager import job_queue_manager
    from packages.queue.models import QueueType, JobPriority

    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    job = await job_queue_manager.enqueue(
        queue=QueueType.WEARABLE_BACKFILL,
        payload={"citizen_id": citizen_id, "days": days, "provider": provider.value if provider else "GARMIN"},
        priority=JobPriority.NORMAL,
        citizen_id=citizen_id,
        tenant_id=current_user.tenant_id,
    )
    return {
        "status": "QUEUED",
        "job_id": job.id,
        "citizen_id": citizen_id,
        "message": f"Timeseries backfill for {days} days enqueued.",
        "status_url": f"/api/v1/jobs/{job.id}",
    }


@router.post("/sync/{citizen_id}/incremental")
async def incremental_sync_wearable_data(
    citizen_id: str,
    payload: IncrementalSyncRequest,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Retrieves only new physiological records since the last sync cursor."""
    delta_records, next_cursor = await wearable_adapter.incremental_sync(
        citizen_id=citizen_id, cursor=payload.cursor
    )

    return {
        "status": "INCREMENTAL_SYNC_COMPLETE",
        "citizen_id": citizen_id,
        "delta_records_count": len(delta_records),
        "next_sync_cursor": next_cursor,
        "projection": wearable_adapter.get_projection(citizen_id),
    }


@router.post("/webhooks/{provider}", status_code=status.HTTP_200_OK)
async def ingest_wearable_webhook(
    provider: WearableProvider,
    payload: WebhookPayload,
):
    """Receives asynchronous real-time telemetry pushes from provider webhooks."""
    result = await wearable_adapter.handle_webhook(payload)
    return result


@router.get("/projections/{citizen_id}", response_model=WearableProjection)
async def get_wearable_projections(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Returns aggregated rolling physiological features for clinical decision support."""
    projection = wearable_adapter.get_projection(citizen_id)
    if not projection:
        # Auto-compute if records exist or trigger initial sync
        await wearable_adapter.sync(citizen_id=citizen_id)
        projection = wearable_adapter.get_projection(citizen_id)

    if not projection:
        raise HTTPException(status_code=404, detail="No wearable projection found for citizen.")
    return projection


@router.post("/disconnect/{citizen_id}/{provider}")
async def disconnect_wearable_provider(
    citizen_id: str,
    provider: WearableProvider,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Disconnects citizen from a specific wearable provider."""
    success = await wearable_adapter.disconnect_provider(citizen_id, provider)
    if not success:
        raise HTTPException(status_code=404, detail="Connection not found for provider")
    return {"status": "DISCONNECTED", "provider": provider.value}


@router.post("/consent/revoke/{citizen_id}")
async def revoke_wearable_consent(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Halts all wearable telemetry ingestion and marks connections as revoked."""
    success = await wearable_adapter.revoke_consent(citizen_id)
    return {"status": "CONSENT_REVOKED", "citizen_id": citizen_id}


@router.delete("/data/{citizen_id}")
async def delete_citizen_wearable_data(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Purges all stored wearable biometric timeseries and projections (Right-to-be-Forgotten)."""
    await wearable_adapter.delete_all_wearable_data(citizen_id)
    return {
        "status": "DATA_PURGED",
        "citizen_id": citizen_id,
        "message": "All wearable telemetry and rolling projections have been completely deleted."
    }


@router.get("/{citizen_id}")
async def get_citizen_wearables(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Returns normalized records and rolling projections for citizen."""
    records = wearable_adapter.raw_records.get(citizen_id)
    if not records:
        await wearable_adapter.sync(citizen_id)
        records = wearable_adapter.raw_records.get(citizen_id, [])

    proj = wearable_adapter.get_projection(citizen_id)
    return {
        "citizen_id": citizen_id,
        "total_records": len(records),
        "projection": proj.model_dump() if proj else None,
        "records": [r.model_dump() for r in records[-20:]],  # Return recent 20
    }
