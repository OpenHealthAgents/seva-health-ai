"""Stage 10: Clinical Record Committer & OpenEHR / FHIR Integration.

Strict Rules:
1. INVARIANT: If status is HUMAN_REVIEW_REQUIRED, NO clinical records are written.
2. Only REVIEW_COMPLETED or verified items are committed to:
   - store.observations (FHIR-aligned Observation instances)
   - store.legal_clinical_records (Immutable legal audit entries)
   - store.medications (Active prescription registry)
"""

import time
import uuid
from datetime import datetime, timezone
from typing import List

from services.documents.pipeline.base import BasePipelineStage, PipelineContext, StageResult
from services.documents.models import (
    IngestionStatus,
    FieldReviewStatus,
)
from packages.clinical_models.observations import Observation
from services.store import store


class ClinicalRecordCommitterStage(BasePipelineStage):
    """Commits verified clinical extractions into persistent patient records and observations."""

    name = "CLINICAL_RECORD_COMMITTER"

    async def process(self, context: PipelineContext) -> StageResult:
        start_time = time.time()
        job = context.job
        bundle = job.extractions
        citizen_id = job.citizen_id

        # 1. Gate: Do NOT commit if human review is pending
        if job.status == IngestionStatus.HUMAN_REVIEW_REQUIRED:
            elapsed = time.time() - start_time
            job.pipeline_stage_timings[self.name] = elapsed
            return StageResult(
                stage_name=self.name,
                success=True,
                message="SAFETY GATE: Document enqueued in Human Review Queue. Zero unvalidated values committed to clinical record.",
                execution_seconds=elapsed,
            )

        # 2. Promote confirmed tests to store.observations
        committed_obs_ids: List[str] = []
        if citizen_id not in store.observations:
            store.observations[citizen_id] = []

        for test in bundle.tests:
            # Check field review status
            if test.review_status in [
                FieldReviewStatus.AUTO_ACCEPTED,
                FieldReviewStatus.REVIEWER_APPROVED,
                FieldReviewStatus.REVIEWER_CORRECTED,
            ]:
                if test.numeric_value is not None:
                    code_sym = test.canonical_name.upper().replace(" ", "_")
                    is_abnormal = test.interpretation in ["HIGH", "LOW", "CRITICAL"]

                    obs = Observation(
                        citizen_id=citizen_id,
                        code=code_sym,
                        value=test.numeric_value,
                        unit=test.normalized_unit or "",
                        source="CLINICAL_DOCUMENT_INGESTION",
                        tenant_id="karnataka_state_health",
                        loinc_code=test.loinc_code or "99999-9",
                        display_name=test.canonical_name,
                        is_abnormal=is_abnormal,
                    )
                    store.observations[citizen_id].append(obs)
                    committed_obs_ids.append(obs.id)

        job.committed_observation_ids = committed_obs_ids

        # 3. Commit confirmed medications to store.medications
        if citizen_id not in store.medications:
            store.medications[citizen_id] = []

        for med in bundle.medications:
            if med.review_status in [
                FieldReviewStatus.AUTO_ACCEPTED,
                FieldReviewStatus.REVIEWER_APPROVED,
                FieldReviewStatus.REVIEWER_CORRECTED,
            ]:
                med_record = {
                    "drug_name": med.drug_name,
                    "dose": f"{med.dose_amount or ''} {med.dose_unit or ''}".strip(),
                    "frequency": med.frequency,
                    "duration": med.duration,
                    "rxnorm_code": med.rxnorm_code,
                    "source_document_id": context.metadata.document_id,
                    "prescribed_date": bundle.dates.prescription_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                }
                store.medications[citizen_id].append(med_record)

        # 4. Commit official legal record to store.legal_clinical_records
        if citizen_id not in store.legal_clinical_records:
            store.legal_clinical_records[citizen_id] = []

        legal_rec_id = f"legal-doc-{uuid.uuid4().hex[:8]}"
        legal_entry = {
            "record_id": legal_rec_id,
            "citizen_id": citizen_id,
            "source_document_id": context.metadata.document_id,
            "document_title": context.metadata.title,
            "document_type": job.document_type.value,
            "sha256_hash": context.metadata.sha256_hash,
            "label": "CLINICIAN-VERIFIED",
            "committed_observations_count": len(committed_obs_ids),
            "diagnoses": [d.diagnosis_name for d in bundle.diagnoses],
            "committed_at": datetime.now(timezone.utc).isoformat(),
            "status": "COMMITTED_TO_LEGAL_RECORD",
        }
        store.legal_clinical_records[citizen_id].append(legal_entry)
        job.committed_legal_record_id = legal_rec_id

        job.status = IngestionStatus.COMMITTED_TO_CLINICAL_RECORD
        elapsed = time.time() - start_time
        job.pipeline_stage_timings[self.name] = elapsed

        return StageResult(
            stage_name=self.name,
            success=True,
            message=f"Successfully committed {len(committed_obs_ids)} observations and legal record '{legal_rec_id}'",
            execution_seconds=elapsed,
        )
