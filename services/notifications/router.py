"""Notifications & Alerts Service for SevaHealth AI.

Supports multi-channel alerts (SMS, WhatsApp, Push) with distributed tracing
and operational metric recording.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import time

from packages.auth.jwt import get_current_user_token, TokenPayload
from packages.observability.context import CorrelationContext, SpanStage
from packages.observability.tracer import tracer
from packages.observability.metrics import metrics
from packages.observability.sanitizer import HealthcareLogSanitizer

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


class DispatchNotificationRequest(BaseModel):
    citizen_id: str
    channel: str = Field(default="SMS", description="SMS | WHATSAPP | PUSH")
    title: str
    body: str
    priority: str = Field(default="NORMAL", description="NORMAL | URGENT | EMERGENCY")


@router.get("/")
async def get_my_notifications(current_user: TokenPayload = Depends(get_current_user_token)) -> List[Dict[str, Any]]:
    return [
        {
            "id": "notif-001",
            "title": "Welcome to SevaHealth AI",
            "body": "Your preventive health decision intelligence dashboard is ready.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "priority": "INFO",
        },
        {
            "id": "notif-002",
            "title": "Daily Habit Check-in",
            "body": "Don't forget to complete today's post-meal brisk walk to sustain optimal glucose uptake.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "priority": "REMINDER",
        }
    ]


@router.post("/dispatch", status_code=status.HTTP_201_CREATED)
async def dispatch_notification(
    payload: DispatchNotificationRequest,
    current_user: TokenPayload = Depends(get_current_user_token),
) -> Dict[str, Any]:
    """Dispatches a notification across SMS, WhatsApp, or Push with distributed tracing."""
    start_t = time.time()
    clean_body = HealthcareLogSanitizer.sanitize_string(payload.body)

    with tracer.span(
        name="NotificationDispatch",
        stage=SpanStage.NOTIFICATION,
        tags={
            "channel": payload.channel,
            "priority": payload.priority,
            "citizen_id": HealthcareLogSanitizer.mask_citizen_id(payload.citizen_id),
        },
    ) as span:
        # Simulate gateway transmission
        duration_ms = round((time.time() - start_t) * 1000, 2)
        metrics.record_notification(channel=payload.channel, duration_ms=duration_ms, success=True)
        span.add_event("telecom_dispatched", {"channel": payload.channel, "latency_ms": duration_ms})

        return {
            "notification_id": f"notif-{uuid.uuid4().hex[:8]}",
            "correlation_id": CorrelationContext.get_correlation_id(),
            "channel": payload.channel,
            "status": "DISPATCHED",
            "delivery_timestamp": datetime.now(timezone.utc).isoformat(),
            "sanitized_body": clean_body,
        }


class BroadcastNotificationRequest(BaseModel):
    recipient_ids: List[str]
    channel: str = Field(default="SMS", description="SMS | WHATSAPP | PUSH")
    title: str
    body: str


@router.post("/broadcast-async", status_code=status.HTTP_202_ACCEPTED)
async def broadcast_notifications_async(
    payload: BroadcastNotificationRequest,
    current_user: TokenPayload = Depends(get_current_user_token),
) -> Dict[str, Any]:
    """Enqueues high-throughput bulk notifications without blocking caller."""
    from packages.queue.manager import job_queue_manager
    from packages.queue.models import QueueType, JobPriority

    job = await job_queue_manager.enqueue(
        queue=QueueType.NOTIFICATION_DISPATCH,
        payload={
            "recipients": payload.recipient_ids,
            "channel": payload.channel,
            "title": payload.title,
            "body": HealthcareLogSanitizer.sanitize_string(payload.body),
        },
        priority=JobPriority.NORMAL,
        tenant_id=current_user.tenant_id,
    )

    return {
        "status": "QUEUED",
        "job_id": job.id,
        "recipients_count": len(payload.recipient_ids),
        "channel": payload.channel,
        "message": f"Broadcast of {len(payload.recipient_ids)} messages enqueued.",
        "status_url": f"/api/v1/jobs/{job.id}",
    }
