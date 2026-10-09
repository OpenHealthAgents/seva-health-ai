"""Asynchronous Queue & Background Job Models for SevaHealth AI.

Designed for district- and state-scale asynchronous processing:
- Document OCR & Clinical NLP
- Wearable timeseries backfill
- Heavy AI / Multi-Agent workflows
- Population analytics & de-identification
- High-throughput notification dispatch
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class JobPriority(int, Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class QueueType(str, Enum):
    DOCUMENT_OCR = "document_ocr"
    WEARABLE_BACKFILL = "wearable_backfill"
    AI_WORKFLOW = "ai_workflow"
    POPULATION_ANALYTICS = "population_analytics"
    NOTIFICATION_DISPATCH = "notification_dispatch"


class AsyncJob(BaseModel):
    """Execution unit for asynchronous background jobs."""
    id: str = Field(default_factory=lambda: f"job-{uuid.uuid4().hex[:12]}")
    queue: QueueType
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.QUEUED
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    progress_pct: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    correlation_id: Optional[str] = None
    citizen_id: Optional[str] = None
    tenant_id: str = "karnataka_state_health"

    def mark_started(self):
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)
        self.progress_pct = 10.0

    def mark_completed(self, result: Dict[str, Any]):
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.result = result
        self.progress_pct = 100.0
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000.0

    def mark_failed(self, error_msg: str):
        self.completed_at = datetime.now(timezone.utc)
        self.error = error_msg
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000.0
        if self.retry_count < self.max_retries:
            self.status = JobStatus.RETRYING
            self.retry_count += 1
        else:
            self.status = JobStatus.FAILED


class QueueMetrics(BaseModel):
    queue: QueueType
    active_workers: int
    queued_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_processed: int
    avg_latency_ms: float
    throughput_per_sec: float
