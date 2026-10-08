"""FastAPI Router for Clinical Document Ingestion Subsystem.

Provides:
- POST /api/v1/documents/ingest (10-Stage Ingestion Pipeline)
- GET  /api/v1/documents/jobs/{job_id} (Job status & extracted entities)
- GET  /api/v1/documents/review-queue (Human review queue)
- POST /api/v1/documents/jobs/{job_id}/human-review (Clinician review submission)
- GET  /api/v1/documents/download/{doc_id} (Download preserved original document)
- GET  /api/v1/documents/{citizen_id} (List documents for citizen)
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Response, status
from pydantic import BaseModel

from packages.auth.jwt import get_current_user_token, TokenPayload, require_roles
from packages.types.enums import UserRole
from services.store import store
from services.documents.models import (
    DocumentIngestionJob,
    HumanReviewCorrection,
    IngestionStatus,
)
from services.documents.engine import ingestion_engine

router = APIRouter(prefix="/documents", tags=["Clinical Document Ingestion"])


class HumanReviewSubmissionPayload(BaseModel):
    corrections: List[HumanReviewCorrection]


@router.post(
    "/ingest",
    response_model=DocumentIngestionJob,
    summary="Upload & Execute 10-Stage Clinical Document Ingestion Pipeline",
)
async def ingest_clinical_document(
    citizen_id: str = Form(..., description="Target citizen ID"),
    title: str = Form("Clinical Document", description="Document title"),
    declared_type: Optional[str] = Form(None, description="Optional document type hint"),
    file: UploadFile = File(..., description="PDF or Image file"),
    current_user: TokenPayload = Depends(get_current_user_token),
):
    """Executes:

    Upload -> Virus/File Validation -> Classification -> OCR -> Extraction ->
    Normalization -> Validation -> Clinical Mapping -> Human Review Gate -> Clinical Record.
    """
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail=f"Citizen '{citizen_id}' not found.")

    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    job = await ingestion_engine.ingest_document(
        citizen_id=citizen_id,
        file_content=file_bytes,
        filename=file.filename or "uploaded_document",
        content_type=content_type,
        title=title,
        uploader_id=current_user.sub,
        declared_type=declared_type,
    )

    if job.status == IngestionStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document rejected: {'; '.join(job.errors)}",
        )

    return job


@router.get(
    "/jobs/{job_id}",
    response_model=DocumentIngestionJob,
    summary="Get Status and Extractions for Ingestion Job",
)
async def get_ingestion_job(
    job_id: str,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    job = ingestion_engine.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@router.get(
    "/review-queue",
    response_model=List[DocumentIngestionJob],
    summary="List Documents Held for Human Review",
)
async def list_human_review_queue(
    citizen_id: Optional[str] = None,
    current_user: TokenPayload = Depends(
        require_roles([UserRole.CLINICIAN, UserRole.PUBLIC_HEALTH_ADMIN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Lists documents with status HUMAN_REVIEW_REQUIRED."""
    return ingestion_engine.list_review_queue(citizen_id=citizen_id)


@router.post(
    "/jobs/{job_id}/human-review",
    response_model=DocumentIngestionJob,
    summary="Submit Clinician Review & Promote Verified Data to Clinical Record",
)
async def submit_human_review(
    job_id: str,
    payload: HumanReviewSubmissionPayload,
    current_user: TokenPayload = Depends(
        require_roles([UserRole.CLINICIAN, UserRole.SYSTEM_ADMIN])
    ),
):
    """Submits APPROVE, CORRECT, or REJECT actions for extracted fields.

    Once verified, the committer promotes observations into the legal medical record.
    """
    job = ingestion_engine.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    reviewer_user = store.get_user(current_user.sub)
    reviewer_name = reviewer_user.full_name if reviewer_user else "Dr. Verified Clinician"

    updated_job = await ingestion_engine.apply_human_review(
        job_id=job_id,
        corrections=payload.corrections,
        reviewer_id=current_user.sub,
        reviewer_name=reviewer_name,
    )
    return updated_job


@router.get(
    "/download/{doc_id}",
    summary="Download Preserved Original Document Bytes",
)
async def download_original_document(
    doc_id: str,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    """Retrieves original preserved raw file from immutable document storage."""
    file_record = ingestion_engine.get_document_file(doc_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="Document file not found in storage.")

    return Response(
        content=file_record["raw_bytes"],
        media_type=file_record["content_type"],
        headers={
            "Content-Disposition": f'inline; filename="{file_record["filename"]}"',
            "X-SHA256-Checksum": file_record["sha256_hash"],
        },
    )


# ==============================================================================
# Legacy Endpoints (Maintained for Backward Compatibility)
# ==============================================================================

@router.post("/upload", summary="Legacy Upload Endpoint")
async def upload_medical_document(
    citizen_id: str = Form(...),
    document_type: str = Form("LAB_REPORT"),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: TokenPayload = Depends(get_current_user_token),
):
    """Preserved legacy route forwarding to the comprehensive ingestion engine."""
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    content = await file.read()
    job = await ingestion_engine.ingest_document(
        citizen_id=citizen_id,
        file_content=content,
        filename=file.filename or "uploaded_file",
        content_type=file.content_type or "application/octet-stream",
        title=title,
        uploader_id=current_user.sub,
        declared_type=document_type,
    )

    doc_meta = store.documents[citizen_id][-1]
    return {
        "status": "SUCCESS",
        "document": doc_meta,
        "job_id": job.job_id,
        "ingestion_status": job.status.value,
        "message": f"Document '{file.filename}' processed via ingestion pipeline.",
    }


@router.get("/{citizen_id}", summary="List Citizen Documents")
async def list_citizen_documents(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    return store.documents.get(citizen_id, [])
