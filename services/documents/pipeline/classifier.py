"""Stage 2: Clinical Document Classification.

Classifies incoming clinical documents into:
- LAB_REPORT
- PRESCRIPTION
- DISCHARGE_SUMMARY
- HEALTH_PACKAGE_REPORT
- MEDICAL_REPORT
"""

import time
import re
from typing import Dict, Tuple

from services.documents.pipeline.base import BasePipelineStage, PipelineContext, StageResult
from services.documents.models import DocumentType, IngestionStatus

CLASSIFICATION_RULES = {
    DocumentType.DISCHARGE_SUMMARY: {
        "strong_keywords": [
            "discharge summary", "date of admission", "date of discharge",
            "condition on discharge", "hospital course", "discharge advice",
            "discharge medications", "admission date", "discharge date"
        ],
        "weight": 3.0,
    },
    DocumentType.PRESCRIPTION: {
        "strong_keywords": [
            "rx", "prescription", "tab.", "cap.", "syrup", "dosage:",
            "once daily", "twice daily", "1-0-1", "0-1-0", "1-0-0",
            "before food", "after food", "sos", "sig:"
        ],
        "weight": 2.5,
    },
    DocumentType.HEALTH_PACKAGE_REPORT: {
        "strong_keywords": [
            "health package", "executive health check", "master health checkup",
            "annual health check", "comprehensive wellness check", "health checkup package"
        ],
        "weight": 3.0,
    },
    DocumentType.LAB_REPORT: {
        "strong_keywords": [
            "lab report", "investigation report", "reference range", "bio-chemistry",
            "hematology", "biochemistry", "pathology", "test name", "observed value",
            "specimen", "fasting blood glucose", "hba1c", "serum creatinine",
            "lipid profile", "complete blood count", "nabl accredited"
        ],
        "weight": 2.0,
    },
    DocumentType.MEDICAL_REPORT: {
        "strong_keywords": [
            "clinical summary", "medical report", "consultation note", "opd report",
            "chief complaint", "history of present illness", "clinical impression"
        ],
        "weight": 2.0,
    },
}


class DocumentClassificationStage(BasePipelineStage):
    """Assigns document type and classification confidence score."""

    name = "DOCUMENT_CLASSIFICATION"

    async def process(self, context: PipelineContext) -> StageResult:
        start_time = time.time()
        context.job.status = IngestionStatus.CLASSIFYING

        # Check preliminary text available or document title / filename
        title_text = f"{context.metadata.title} {context.metadata.filename}".lower()
        extracted_text = context.extracted_text.lower() if context.extracted_text else ""
        corpus = f"{title_text} {extracted_text}"

        scores: Dict[DocumentType, float] = {}

        for doc_type, rule in CLASSIFICATION_RULES.items():
            score = 0.0
            for kw in rule["strong_keywords"]:
                count = corpus.count(kw)
                if count > 0:
                    score += rule["weight"] * min(count, 3)
            scores[doc_type] = score

        best_type = DocumentType.UNKNOWN
        best_score = 0.0

        for doc_type, score in scores.items():
            if score > best_score:
                best_score = score
                best_type = doc_type

        # If best_score is minimal, check title fallback or default to LAB_REPORT if laboratory cues exist
        if best_score < 2.0:
            if "lab" in title_text or "report" in title_text or "test" in title_text:
                best_type = DocumentType.LAB_REPORT
                confidence = 0.70
            elif "rx" in title_text or "prescription" in title_text:
                best_type = DocumentType.PRESCRIPTION
                confidence = 0.70
            elif "discharge" in title_text:
                best_type = DocumentType.DISCHARGE_SUMMARY
                confidence = 0.75
            else:
                best_type = DocumentType.MEDICAL_REPORT
                confidence = 0.60
        else:
            confidence = min(0.98, 0.65 + (best_score * 0.05))

        context.job.document_type = best_type
        context.job.classification_confidence = round(confidence, 3)

        elapsed = time.time() - start_time
        context.job.pipeline_stage_timings[self.name] = elapsed

        return StageResult(
            stage_name=self.name,
            success=True,
            message=f"Classified as {best_type.value} with confidence {confidence:.2f}",
            execution_seconds=elapsed,
        )
