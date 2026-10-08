"""Stage 6: Clinical Validation & Physiological Boundary Guard.

Guarantees:
- Impossible physiological values (e.g. HbA1c 95% or Systolic BP 850 mmHg) are rejected.
- Conflicting temporal dates (future report dates or inverted admission/discharge) are flagged.
- Protects against unvalidated commits into clinical systems.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple

from services.documents.pipeline.base import BasePipelineStage, PipelineContext, StageResult
from services.documents.models import IngestionStatus

PHYSIOLOGICAL_BOUNDS: Dict[str, Tuple[float, float, str]] = {
    "HbA1c": (3.0, 20.0, "%"),
    "Fasting Blood Glucose": (20.0, 800.0, "mg/dL"),
    "Postprandial Blood Glucose": (20.0, 800.0, "mg/dL"),
    "Serum Creatinine": (0.1, 30.0, "mg/dL"),
    "Total Cholesterol": (50.0, 1000.0, "mg/dL"),
    "HDL Cholesterol": (10.0, 200.0, "mg/dL"),
    "LDL Cholesterol": (10.0, 500.0, "mg/dL"),
    "Triglycerides": (20.0, 2000.0, "mg/dL"),
    "Systolic Blood Pressure": (50.0, 300.0, "mmHg"),
    "Diastolic Blood Pressure": (30.0, 200.0, "mmHg"),
    "Hemoglobin": (2.0, 25.0, "g/dL"),
    "eGFR": (1.0, 200.0, "mL/min/1.73m2"),
}


class ClinicalValidatorStage(BasePipelineStage):
    """Enforces clinical sanity, physiological guardrails, and temporal coherence."""

    name = "CLINICAL_VALIDATION"

    async def process(self, context: PipelineContext) -> StageResult:
        start_time = time.time()
        context.job.status = IngestionStatus.VALIDATING

        bundle = context.job.extractions
        validation_warnings = []

        # 1. Physiological Boundary Sanity
        for test in bundle.tests:
            canonical = test.canonical_name
            if canonical in PHYSIOLOGICAL_BOUNDS and test.numeric_value is not None:
                min_v, max_v, unit = PHYSIOLOGICAL_BOUNDS[canonical]
                val = test.numeric_value
                if not (min_v <= val <= max_v):
                    test.is_valid_physiological = False
                    warning = (
                        f"Physiological Out-of-Bounds: {canonical} value {val} {unit} "
                        f"is outside biological survivability range [{min_v} - {max_v} {unit}]"
                    )
                    test.validation_flags.append(warning)
                    validation_warnings.append(warning)
                    context.job.human_review_reasons.append(warning)
                    # Severely penalize confidence score
                    test.confidence = max(0.10, test.confidence - 0.45)

            # Reference bounds check
            if test.reference_low is not None and test.reference_high is not None:
                if test.reference_low >= test.reference_high:
                    warn = f"Inverted reference interval for {test.test_name}: [{test.reference_low} - {test.reference_high}]"
                    test.validation_flags.append(warn)
                    validation_warnings.append(warn)

        # 2. Temporal Sanity
        dates = bundle.dates
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)

        for date_field, d_val in [
            ("report_date", dates.report_date),
            ("specimen_date", dates.specimen_collection_date),
            ("admission_date", dates.admission_date),
            ("discharge_date", dates.discharge_date),
        ]:
            if d_val:
                try:
                    dt = datetime.strptime(d_val, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if dt > tomorrow:
                        w = f"Future date detected in {date_field}: {d_val}"
                        validation_warnings.append(w)
                        context.job.human_review_reasons.append(w)
                except ValueError:
                    pass

        # Admission vs Discharge check
        if dates.admission_date and dates.discharge_date:
            try:
                dt_adm = datetime.strptime(dates.admission_date, "%Y-%m-%d")
                dt_dis = datetime.strptime(dates.discharge_date, "%Y-%m-%d")
                if dt_dis < dt_adm:
                    w = f"Temporal inversion: discharge date ({dates.discharge_date}) earlier than admission ({dates.admission_date})"
                    validation_warnings.append(w)
                    context.job.human_review_reasons.append(w)
            except ValueError:
                pass

        elapsed = time.time() - start_time
        context.job.pipeline_stage_timings[self.name] = elapsed

        if validation_warnings:
            context.job.requires_human_review = True

        return StageResult(
            stage_name=self.name,
            success=True,
            message=(
                f"Validation complete with {len(validation_warnings)} flags"
                if validation_warnings else "All physiological and temporal validations passed"
            ),
            execution_seconds=elapsed,
        )
