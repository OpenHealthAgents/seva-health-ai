"""Stage 7: Clinical Terminology Mapping Engine.

Maps extracted entities to international standard clinical terminologies:
- LOINC for Laboratory Investigations & Physiological Vitals
- RxNorm & ATC for Medications
- SNOMED CT & ICD-10 for Diagnoses
"""

import time
from typing import Dict, Tuple

from services.documents.pipeline.base import BasePipelineStage, PipelineContext, StageResult
from services.documents.models import IngestionStatus

LOINC_ONTOLOGY_MAP: Dict[str, Tuple[str, str]] = {
    "HbA1c": ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood"),
    "Fasting Blood Glucose": ("1558-6", "Fasting glucose [Mass/volume] in Serum or Plasma"),
    "Postprandial Blood Glucose": ("1521-4", "Glucose [Mass/volume] in Blood 2 hours post meal"),
    "Serum Creatinine": ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma"),
    "Total Cholesterol": ("2093-3", "Cholesterol [Mass/volume] in Serum or Plasma"),
    "HDL Cholesterol": ("2085-9", "Cholesterol in HDL [Mass/volume] in Serum or Plasma"),
    "LDL Cholesterol": ("2089-1", "Cholesterol in LDL [Mass/volume] in Serum or Plasma"),
    "Triglycerides": ("2571-8", "Triglyceride [Mass/volume] in Serum or Plasma"),
    "Systolic Blood Pressure": ("8480-6", "Systolic blood pressure"),
    "Diastolic Blood Pressure": ("8462-4", "Diastolic blood pressure"),
    "Hemoglobin": ("718-7", "Hemoglobin [Mass/volume] in Blood"),
    "eGFR": ("33914-3", "Glomerular filtration rate/1.73 sq M.predicted"),
}

RXNORM_ATC_MAP: Dict[str, Tuple[str, str]] = {
    "Metformin": ("6809", "A10BA02"),
    "Telmisartan": ("316049", "C09CA07"),
    "Amlodipine": ("17767", "C08CA01"),
    "Atorvastatin": ("83367", "C10AA05"),
    "Rosuvastatin": ("301542", "C10AA07"),
    "Glimepiride": ("25789", "A10BB12"),
    "Vildagliptin": ("404663", "A10BH02"),
    "Dapagliflozin": ("1488564", "A10BK01"),
    "Aspirin": ("1191", "B01AC06"),
}

SNOMED_ICD10_MAP: Dict[str, Tuple[str, str]] = {
    "Type 2 Diabetes Mellitus": ("44054006", "E11.9"),
    "Essential Hypertension": ("38341003", "I10"),
    "Dyslipidemia": ("370992007", "E78.5"),
    "Chronic Kidney Disease": ("709044004", "N18.9"),
    "Coronary Artery Disease": ("53741008", "I25.1"),
    "Obesity": ("414916001", "E66.9"),
}


class ClinicalMapperStage(BasePipelineStage):
    """Binds extracted entities to authoritative standard terminologies (LOINC, RxNorm, SNOMED)."""

    name = "CLINICAL_MAPPING"

    async def process(self, context: PipelineContext) -> StageResult:
        start_time = time.time()
        context.job.status = IngestionStatus.MAPPING_CLINICAL

        bundle = context.job.extractions
        mapped_count = 0

        # 1. Map Tests to LOINC
        for test in bundle.tests:
            canonical = test.canonical_name
            if canonical in LOINC_ONTOLOGY_MAP:
                code, display = LOINC_ONTOLOGY_MAP[canonical]
                test.loinc_code = code
                test.loinc_display = display
                mapped_count += 1

        # 2. Map Medications to RxNorm & ATC
        for med in bundle.medications:
            d_name = med.drug_name
            if d_name in RXNORM_ATC_MAP:
                rxn, atc = RXNORM_ATC_MAP[d_name]
                med.rxnorm_code = rxn
                med.atc_code = atc
                mapped_count += 1

        # 3. Map Diagnoses to SNOMED CT & ICD-10
        for diag in bundle.diagnoses:
            d_name = diag.diagnosis_name
            if d_name in SNOMED_ICD10_MAP:
                snomed, icd = SNOMED_ICD10_MAP[d_name]
                diag.snomed_ct_code = snomed
                diag.icd10_code = icd
                mapped_count += 1

        elapsed = time.time() - start_time
        context.job.pipeline_stage_timings[self.name] = elapsed

        return StageResult(
            stage_name=self.name,
            success=True,
            message=f"Mapped {mapped_count} entities to standard terminologies (LOINC, RxNorm, SNOMED)",
            execution_seconds=elapsed,
        )
