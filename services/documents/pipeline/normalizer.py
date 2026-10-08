"""Stage 5: Clinical Normalization Engine.

Standardizes:
1. Clinical measurement units (e.g. mg/dl -> mg/dL, mm hg -> mmHg, mmol/mol -> %)
2. Canonical terminology names
3. Temporal dates into ISO-8601 UTC format
4. Clinical interpretations (NORMAL, HIGH, LOW, CRITICAL)
"""

import time
import re
from datetime import datetime
from typing import Optional, Tuple

from services.documents.pipeline.base import BasePipelineStage, PipelineContext, StageResult
from services.documents.models import IngestionStatus, ExtractedLabTest

UNIT_NORMALIZATION_MAP = {
    "mg/dl": "mg/dL",
    "mg/100ml": "mg/dL",
    "mg%": "mg/dL",
    "mg / dl": "mg/dL",
    "mg/l": "mg/L",
    "g/dl": "g/dL",
    "gm/dl": "g/dL",
    "g%": "g/dL",
    "mmhg": "mmHg",
    "mm hg": "mmHg",
    "mm_hg": "mmHg",
    "%": "%",
    "percent": "%",
    "ml/min/1.73m2": "mL/min/1.73m2",
    "ml/min": "mL/min/1.73m2",
    "bpm": "bpm",
    "/min": "bpm",
}

CANONICAL_NAME_MAP = {
    "fbs": "Fasting Blood Glucose",
    "fasting blood sugar": "Fasting Blood Glucose",
    "glucose - fasting": "Fasting Blood Glucose",
    "glycated hemoglobin": "HbA1c",
    "glycosylated hemoglobin": "HbA1c",
    "hba1c": "HbA1c",
    "s.creatinine": "Serum Creatinine",
    "creatinine - serum": "Serum Creatinine",
    "serum creatinine": "Serum Creatinine",
    "sbp": "Systolic Blood Pressure",
    "systolic bp": "Systolic Blood Pressure",
    "dbp": "Diastolic Blood Pressure",
    "diastolic bp": "Diastolic Blood Pressure",
    "total cholesterol": "Total Cholesterol",
    "hdl cholesterol": "HDL Cholesterol",
    "ldl cholesterol": "LDL Cholesterol",
    "triglycerides": "Triglycerides",
    "hemoglobin": "Hemoglobin",
    "egfr": "eGFR",
}


class ClinicalNormalizerStage(BasePipelineStage):
    """Normalizes units, canonical names, dates, and calculates clinical interpretations."""

    name = "CLINICAL_NORMALIZATION"

    async def process(self, context: PipelineContext) -> StageResult:
        start_time = time.time()
        context.job.status = IngestionStatus.NORMALIZING

        bundle = context.job.extractions

        # 1. Normalize Tests
        for test in bundle.tests:
            # Canonical name
            test_key = test.test_name.lower().strip()
            test.canonical_name = CANONICAL_NAME_MAP.get(test_key, test.test_name)

            # Unit normalization
            raw_unit = (test.raw_unit or "").strip().lower()
            normalized_u = UNIT_NORMALIZATION_MAP.get(raw_unit, test.raw_unit)
            test.normalized_unit = normalized_u

            # Check IFCC HbA1c conversion (mmol/mol -> %)
            if test.canonical_name == "HbA1c" and raw_unit == "mmol/mol" and test.numeric_value:
                # NGSP formula: (0.09148 * mmol/mol) + 2.152
                converted = (0.09148 * test.numeric_value) + 2.152
                test.numeric_value = round(converted, 1)
                test.normalized_unit = "%"

            # Clinical interpretation
            test.interpretation = self._determine_interpretation(test)

        # 2. Normalize Dates
        dates = bundle.dates
        if dates.report_date:
            dates.report_date = self._normalize_date_str(dates.report_date)
        if dates.specimen_collection_date:
            dates.specimen_collection_date = self._normalize_date_str(dates.specimen_collection_date)
        if dates.admission_date:
            dates.admission_date = self._normalize_date_str(dates.admission_date)
        if dates.discharge_date:
            dates.discharge_date = self._normalize_date_str(dates.discharge_date)

        elapsed = time.time() - start_time
        context.job.pipeline_stage_timings[self.name] = elapsed

        return StageResult(
            stage_name=self.name,
            success=True,
            message=f"Normalized {len(bundle.tests)} tests and associated dates",
            execution_seconds=elapsed,
        )

    def _determine_interpretation(self, test: ExtractedLabTest) -> str:
        val = test.numeric_value
        if val is None:
            return "NORMAL"

        name = test.canonical_name

        # Critical threshold checks
        if name == "Fasting Blood Glucose":
            if val >= 300.0 or val <= 50.0:
                return "CRITICAL"
            elif val >= 126.0:
                return "HIGH"
            elif val >= 100.0:
                return "HIGH"  # Impaired
            elif val < 70.0:
                return "LOW"
            return "NORMAL"

        if name == "HbA1c":
            if val >= 10.0:
                return "CRITICAL"
            elif val >= 6.5:
                return "HIGH"
            elif val >= 5.7:
                return "HIGH"  # Prediabetes
            return "NORMAL"

        if name == "Systolic Blood Pressure":
            if val >= 180.0 or val < 70.0:
                return "CRITICAL"
            elif val >= 130.0:
                return "HIGH"
            elif val < 90.0:
                return "LOW"
            return "NORMAL"

        # Generic range evaluation if reference bounds exist
        if test.reference_high is not None and val > test.reference_high:
            return "HIGH"
        if test.reference_low is not None and val < test.reference_low:
            return "LOW"

        return "NORMAL"

    def _normalize_date_str(self, d_str: str) -> str:
        """Converts DD/MM/YYYY, DD-MMM-YYYY, etc. to ISO-8601 (YYYY-MM-DD)."""
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%d-%b-%Y", "%d-%B-%Y",
            "%Y-%m-%d", "%Y/%m/%d"
        ]
        clean_str = d_str.strip()
        for fmt in formats:
            try:
                dt = datetime.strptime(clean_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return clean_str
