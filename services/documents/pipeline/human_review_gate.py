"""Stage 8: Human-in-the-Loop Review Gate.

Enforces:
1. Strict Confidence Thresholds (minimum 0.85).
2. Routing of low-confidence, out-of-range, or ambiguous clinical fields to the Human Review Queue.
3. INVARIANT: Never automatically commit uncertain extracted clinical values without validation.
"""

import time
from typing import List

from services.documents.pipeline.base import BasePipelineStage, PipelineContext, StageResult
from services.documents.models import (
    IngestionStatus,
    FieldReviewStatus,
)

HUMAN_REVIEW_CONFIDENCE_THRESHOLD = 0.85


class HumanReviewGateStage(BasePipelineStage):
    """Evaluates field-level extraction confidence and gates unverified data from clinical records."""

    name = "HUMAN_REVIEW_GATE"

    async def process(self, context: PipelineContext) -> StageResult:
        start_time = time.time()
        bundle = context.job.extractions

        all_confidences: List[float] = []
        low_confidence_items: List[str] = []

        # 1. Evaluate Patient Confidence
        p = bundle.patient
        if p.patient_name:
            all_confidences.append(p.patient_name_confidence)
            if p.patient_name_confidence < HUMAN_REVIEW_CONFIDENCE_THRESHOLD:
                low_confidence_items.append(f"Low confidence patient name ({p.patient_name_confidence:.2f})")
        else:
            low_confidence_items.append("Missing patient identifier name in extracted document")

        if p.abha_id:
            all_confidences.append(p.abha_id_confidence)

        # 2. Evaluate Laboratory & Vital Tests
        for test in bundle.tests:
            all_confidences.append(test.confidence)

            # Physiological out-of-bounds trigger
            if not test.is_valid_physiological:
                test.review_status = FieldReviewStatus.PENDING_REVIEW
                low_confidence_items.append(f"Physiological violation in {test.test_name}: {test.numeric_value} {test.normalized_unit}")

            # Low confidence score
            elif test.confidence < HUMAN_REVIEW_CONFIDENCE_THRESHOLD:
                test.review_status = FieldReviewStatus.PENDING_REVIEW
                low_confidence_items.append(f"Low confidence test: {test.test_name} ({test.confidence:.2f})")

            # Missing LOINC mapping
            elif not test.loinc_code:
                test.review_status = FieldReviewStatus.PENDING_REVIEW
                low_confidence_items.append(f"Unmapped laboratory code for: {test.test_name}")

            else:
                test.review_status = FieldReviewStatus.AUTO_ACCEPTED

        # 3. Evaluate Medications
        for med in bundle.medications:
            all_confidences.append(med.confidence)
            if med.confidence < HUMAN_REVIEW_CONFIDENCE_THRESHOLD:
                med.review_status = FieldReviewStatus.PENDING_REVIEW
                low_confidence_items.append(f"Low confidence medication: {med.drug_name} ({med.confidence:.2f})")
            else:
                med.review_status = FieldReviewStatus.AUTO_ACCEPTED

        # 4. Evaluate Diagnoses
        for diag in bundle.diagnoses:
            all_confidences.append(diag.confidence)
            if diag.confidence < HUMAN_REVIEW_CONFIDENCE_THRESHOLD:
                diag.review_status = FieldReviewStatus.PENDING_REVIEW
                low_confidence_items.append(f"Low confidence diagnosis: {diag.diagnosis_name} ({diag.confidence:.2f})")
            else:
                diag.review_status = FieldReviewStatus.AUTO_ACCEPTED

        mean_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.50
        bundle.mean_confidence = round(mean_conf, 3)
        bundle.low_confidence_fields_count = len(low_confidence_items)
        context.job.overall_confidence = bundle.mean_confidence

        for reason in low_confidence_items:
            if reason not in context.job.human_review_reasons:
                context.job.human_review_reasons.append(reason)

        elapsed = time.time() - start_time
        context.job.pipeline_stage_timings[self.name] = elapsed

        # Trigger Human Review if ANY low-confidence items exist or physiological violations occurred
        if low_confidence_items or context.job.requires_human_review:
            context.job.requires_human_review = True
            context.job.status = IngestionStatus.HUMAN_REVIEW_REQUIRED
            return StageResult(
                stage_name=self.name,
                success=True,
                message=f"Flagged for Human Review: {len(low_confidence_items)} ambiguous or low-confidence fields",
                execution_seconds=elapsed,
            )
        else:
            context.job.requires_human_review = False
            context.job.status = IngestionStatus.REVIEW_COMPLETED
            return StageResult(
                stage_name=self.name,
                success=True,
                message="High-confidence extraction; ready for clinical record promotion",
                execution_seconds=elapsed,
            )
