"""API Router for Background Asynchronous Job Processing & Monitoring.

Allows client apps (mobile, web) to poll job progress non-blockingly:
- Check OCR completion
- Check wearable backfill status
- Monitor AI multi-agent workflows
- Track population analytics generation
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field

from packages.auth.jwt import get_current_user_token, TokenPayload
from packages.queue.models import (
    JobStatus,
    JobPriority,
    QueueType,
    AsyncJob,
    QueueMetrics,
)
from packages.queue.manager import job_queue_manager

router = APIRouter(prefix="/jobs", tags=["Asynchronous Background Jobs"])


class JobSubmitRequest(BaseModel):
    queue: QueueType
    payload: Dict[str, Any]
    priority: JobPriority = JobPriority.NORMAL
    citizen_id: Optional[str] = None


@router.post("/submit", response_model=AsyncJob, status_code=status.HTTP_202_ACCEPTED)
async def submit_async_job(
    req: JobSubmitRequest,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    """Enqueues an asynchronous job for background processing without blocking caller."""
    job = await job_queue_manager.enqueue(
        queue=req.queue,
        payload=req.payload,
        priority=req.priority,
        citizen_id=req.citizen_id or (current_user.sub if current_user.role == "CITIZEN" else None),
        tenant_id=current_user.tenant_id,
    )
    return job


@router.get("/{job_id}", response_model=AsyncJob)
async def get_job_status(
    job_id: str,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    """Retrieves current execution status, progress, and result of a background job."""
    job = job_queue_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@router.get("/", response_model=List[AsyncJob])
async def list_jobs(
    queue: Optional[QueueType] = Query(None),
    status: Optional[JobStatus] = Query(None),
    citizen_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenPayload = Depends(get_current_user_token),
):
    """Lists recent background jobs with optional filtering."""
    return job_queue_manager.list_jobs(
        queue=queue,
        status=status,
        citizen_id=citizen_id,
        limit=limit,
    )


@router.get("/metrics/{queue_type}", response_model=QueueMetrics)
async def get_queue_metrics(
    queue_type: QueueType,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    """Retrieves operational throughput and latency statistics for a specific queue."""
    return job_queue_manager.get_queue_metrics(queue_type)


@router.post("/cancel/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    """Cancels a pending or queued background job."""
    job = job_queue_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed or failed job.")
    job.status = JobStatus.CANCELLED
    return {"status": "CANCELLED", "job_id": job_id}
