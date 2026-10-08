"""Stage 4: Structured Clinical Entity Extraction.

Extracts:
1. Patient Identifiers (Name, ABHA ID, Age, Gender, MRN)
2. Laboratory & Vital Tests (Test name, raw value, raw unit, reference range)
3. Dates (Report date, specimen date, prescription date, admission, discharge)
4. Medications (Drug name, dose, frequency, duration, instructions)
5. Diagnoses (Primary, secondary, provisional)
6. Provider Information (Doctor name, registration number, specialty)
7. Facility Information (Hospital / Lab name, accreditation)
"""

import time
import re
from typing import List, Optional, Tuple

from services.documents.pipeline.base import BasePipelineStage, PipelineContext, StageResult
from services.documents.models import (
    IngestionStatus,
    ClinicalExtractionBundle,
    ExtractedPatientInfo,
    ExtractedLabTest,
    ExtractedMedication,
    ExtractedDiagnosis,
    ExtractedProvider,
    ExtractedFacility,
    ExtractedDates,
    ProvenanceRecord,
)

# Known laboratory test patterns
KNOWN_TEST_PATTERNS = [
    {
        "name": "HbA1c",
        "patterns": [r"(?:hba1c|glycated\s+hemoglobin|glycosylated\s+hemoglobin)"],
        "default_unit": "%",
    },
    {
        "name": "Fasting Blood Glucose",
        "patterns": [r"(?:fasting\s+blood\s+glucose|fasting\s+blood\s+sugar|fbs|glucose\s*-\s*fasting)"],
        "default_unit": "mg/dL",
    },
    {
        "name": "Postprandial Blood Glucose",
        "patterns": [r"(?:postprandial\s+blood\s+glucose|ppbs|glucose\s*-\s*post\s*prandial)"],
        "default_unit": "mg/dL",
    },
    {
        "name": "Serum Creatinine",
        "patterns": [r"(?:serum\s+creatinine|creatinine\s*-\s*serum|s\.creatinine)"],
        "default_unit": "mg/dL",
    },
    {
        "name": "Total Cholesterol",
        "patterns": [r"(?:total\s+cholesterol|cholesterol\s*-\s*total)"],
        "default_unit": "mg/dL",
    },
    {
        "name": "HDL Cholesterol",
        "patterns": [r"(?:hdl\s+cholesterol|cholesterol\s*-\s*hdl)"],
        "default_unit": "mg/dL",
    },
    {
        "name": "LDL Cholesterol",
        "patterns": [r"(?:ldl\s+cholesterol|cholesterol\s*-\s*ldl)"],
        "default_unit": "mg/dL",
    },
    {
        "name": "Triglycerides",
        "patterns": [r"(?:triglycerides|serum\s+triglycerides)"],
        "default_unit": "mg/dL",
    },
    {
        "name": "Systolic Blood Pressure",
        "patterns": [r"(?:systolic\s+bp|systolic\s+blood\s+pressure|sbp)"],
        "default_unit": "mmHg",
    },
    {
        "name": "Diastolic Blood Pressure",
        "patterns": [r"(?:diastolic\s+bp|diastolic\s+blood\s+pressure|dbp)"],
        "default_unit": "mmHg",
    },
    {
        "name": "Hemoglobin",
        "patterns": [r"(?:hemoglobin|haemoglobin|hb\b)"],
        "default_unit": "g/dL",
    },
    {
        "name": "eGFR",
        "patterns": [r"(?:egfr|estimated\s+gfr)"],
        "default_unit": "mL/min/1.73m2",
    },
]

# Medication extraction patterns
KNOWN_MEDICATION_NAMES = [
    "Metformin", "Telmisartan", "Amlodipine", "Atorvastatin", "Rosuvastatin",
    "Glimepiride", "Vildagliptin", "Dapagliflozin", "Empagliflozin", "Enalapril",
    "Losartan", "Hydrochlorothiazide", "Aspirin", "Clopidogrel", "Pantoprazole",
    "Paracetamol", "Insulin Glargine"
]


class ClinicalEntityExtractorStage(BasePipelineStage):
    """Extracts granular clinical entities with exact line and provenance coordinates."""

    name = "CLINICAL_ENTITY_EXTRACTION"

    async def process(self, context: PipelineContext) -> StageResult:
        start_time = time.time()
        context.job.status = IngestionStatus.EXTRACTING

        raw_text = context.extracted_text
        doc_id = context.metadata.document_id
        file_hash = context.metadata.sha256_hash

        bundle = ClinicalExtractionBundle()

        # 1. Patient Identifiers Extraction
        bundle.patient = self._extract_patient_info(context, doc_id, file_hash)

        # 2. Dates Extraction
        bundle.dates = self._extract_dates(context, doc_id, file_hash)

        # 3. Provider & Facility Extraction
        bundle.provider = self._extract_provider(context, doc_id, file_hash)
        bundle.facility = self._extract_facility(context, doc_id, file_hash)

        # 4. Laboratory Tests & Vitals Extraction
        bundle.tests = self._extract_lab_tests(context, doc_id, file_hash)

        # 5. Medications Extraction
        bundle.medications = self._extract_medications(context, doc_id, file_hash)

        # 6. Diagnoses Extraction
        bundle.diagnoses = self._extract_diagnoses(context, doc_id, file_hash)

        context.job.extractions = bundle

        elapsed = time.time() - start_time
        context.job.pipeline_stage_timings[self.name] = elapsed

        total_extracted = (
            len(bundle.tests) +
            len(bundle.medications) +
            len(bundle.diagnoses) +
            (1 if bundle.patient.patient_name else 0)
        )

        return StageResult(
            stage_name=self.name,
            success=True,
            message=f"Extracted {total_extracted} clinical entities (Tests: {len(bundle.tests)}, Meds: {len(bundle.medications)}, Diags: {len(bundle.diagnoses)})",
            execution_seconds=elapsed,
        )

    def _extract_patient_info(self, ctx: PipelineContext, doc_id: str, file_hash: str) -> ExtractedPatientInfo:
        info = ExtractedPatientInfo()
        lines = ctx.ocr_lines

        for item in lines:
            text = item["text"]
            page = item["page"]
            line_no = item["line"]

            # Name match
            if not info.patient_name:
                name_match = re.search(
                    r"(?:Patient\s*Name|Pt\.?\s*Name|Name)\s*[:\-]\s*([A-Za-z\s\.\']{2,35}?)(?=\s+(?:ABHA|Age|Gender|Sex|MRN|UHID|PID|DOB|Date)|\n|$)",
                    text,
                    re.I,
                )
                if name_match:
                    candidate = name_match.group(1).strip()
                    if candidate.lower() not in ["age", "sex", "male", "female", "date"]:
                        info.patient_name = candidate
                        info.patient_name_confidence = 0.92

                        info.provenance = ProvenanceRecord(
                            source_document_id=doc_id,
                            file_sha256=file_hash,
                            page_number=page,
                            line_number=line_no,
                            raw_text_snippet=text,
                        )

            # ABHA ID match (e.g., 91-4829-1029-4820 or ABHA: 14 digits)
            if not info.abha_id:
                abha_match = re.search(r"(?:ABHA(?:\s*ID|\s*Number)?)\s*[:\-]?\s*(\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})", text, re.I)
                if abha_match:
                    info.abha_id = abha_match.group(1).strip().replace(" ", "-")
                    info.abha_id_confidence = 0.96

            # Age match
            if info.age is None:
                age_match = re.search(r"(?:Age|Yrs?)\s*[:\-]?\s*(\d{1,3})\s*(?:Y|Yrs|Years)?", text, re.I)
                if age_match:
                    try:
                        parsed_age = int(age_match.group(1))
                        if 0 <= parsed_age <= 120:
                            info.age = parsed_age
                            info.age_confidence = 0.90
                    except ValueError:
                        pass

            # Gender match
            if not info.gender:
                gender_match = re.search(r"(?:Gender|Sex)\s*[:\-]?\s*(MALE|FEMALE|OTHER|M|F)\b", text, re.I)
                if gender_match:
                    g = gender_match.group(1).upper()
                    info.gender = "MALE" if g in ["M", "MALE"] else ("FEMALE" if g in ["F", "FEMALE"] else "OTHER")
                    info.gender_confidence = 0.95

            # MRN / Patient ID
            if not info.mrn_or_patient_id:
                mrn_match = re.search(r"(?:MRN|Patient\s*ID|UHID|PID)\s*[:\-]?\s*([A-Za-z0-9\-]{4,20})", text, re.I)
                if mrn_match:
                    info.mrn_or_patient_id = mrn_match.group(1).strip()
                    info.mrn_confidence = 0.90

        return info

    def _extract_dates(self, ctx: PipelineContext, doc_id: str, file_hash: str) -> ExtractedDates:
        dates = ExtractedDates()
        lines = ctx.ocr_lines

        date_pattern = r"(\d{1,2}[-/\.](?:\d{1,2}|[A-Za-z]{3})[-/\.]\d{2,4})"

        for item in lines:
            text = item["text"]
            page = item["page"]
            line_no = item["line"]

            if not dates.report_date:
                m = re.search(rf"(?:Report\s*Date|Date\s*of\s*Report|Date)\s*[:\-]?\s*{date_pattern}", text, re.I)
                if m:
                    dates.report_date = m.group(1).strip()
                    dates.confidence = 0.88
                    dates.provenance = ProvenanceRecord(
                        source_document_id=doc_id,
                        file_sha256=file_hash,
                        page_number=page,
                        line_number=line_no,
                        raw_text_snippet=text,
                    )

            if not dates.admission_date:
                m = re.search(rf"(?:Date\s*of\s*Admission|Admission\s*Date|DOA)\s*[:\-]?\s*{date_pattern}", text, re.I)
                if m:
                    dates.admission_date = m.group(1).strip()

            if not dates.discharge_date:
                m = re.search(rf"(?:Date\s*of\s*Discharge|Discharge\s*Date|DOD)\s*[:\-]?\s*{date_pattern}", text, re.I)
                if m:
                    dates.discharge_date = m.group(1).strip()

        return dates

    def _extract_provider(self, ctx: PipelineContext, doc_id: str, file_hash: str) -> ExtractedProvider:
        prov = ExtractedProvider()
        for item in ctx.ocr_lines:
            text = item["text"]
            m = re.search(
                r"(?:Doctor|Dr\.?|Consultant|Pathologist|Physician)\s*[:\-]?\s*(Dr\.?\s*[A-Za-z\s\.\']{3,30}?)(?=\s+(?:MD|MBBS|MS|DM|DNB|Reg|Registration|KMC|Licence|License)|\n|$)",
                text,
                re.I,
            )
            if not m:
                m = re.search(r"(?:Doctor|Dr\.?|Consultant|Pathologist|Physician)\s*[:\-]?\s*(Dr\.?\s*[A-Za-z\s\.\']{3,30})", text, re.I)
            if m and not prov.doctor_name:
                prov.doctor_name = m.group(1).strip()

                prov.confidence = 0.88
                prov.provenance = ProvenanceRecord(
                    source_document_id=doc_id,
                    file_sha256=file_hash,
                    page_number=item["page"],
                    line_number=item["line"],
                    raw_text_snippet=text,
                )

            m_reg = re.search(r"(?:Reg(?:istration)?\.?\s*(?:No|Number)?)\s*[:\-]?\s*([A-Za-z0-9\/\-]{4,20})", text, re.I)
            if m_reg and not prov.registration_number:
                prov.registration_number = m_reg.group(1).strip()

        return prov

    def _extract_facility(self, ctx: PipelineContext, doc_id: str, file_hash: str) -> ExtractedFacility:
        fac = ExtractedFacility()
        for item in ctx.ocr_lines[:15]:  # Look at headers
            text = item["text"]
            if any(h in text.lower() for h in ["hospital", "clinic", "diagnostic", "laboratory", "health centre", "phc", "chc"]):
                fac.facility_name = text.strip()
                fac.confidence = 0.85
                fac.provenance = ProvenanceRecord(
                    source_document_id=doc_id,
                    file_sha256=file_hash,
                    page_number=item["page"],
                    line_number=item["line"],
                    raw_text_snippet=text,
                )
                if "nabl" in text.lower():
                    fac.accreditation = "NABL"
                break
        return fac

    def _extract_lab_tests(self, ctx: PipelineContext, doc_id: str, file_hash: str) -> List[ExtractedLabTest]:
        tests: List[ExtractedLabTest] = []
        lines = ctx.ocr_lines

        for item in lines:
            text = item["text"]
            page = item["page"]
            line_no = item["line"]

            for test_def in KNOWN_TEST_PATTERNS:
                for pat in test_def["patterns"]:
                    match = re.search(pat, text, re.I)
                    if match:
                        # Extract value and unit from line
                        # Typical line: "HbA1c 6.8 % 4.0 - 5.6" or "Fasting Blood Sugar: 126.0 mg/dL (70 - 100)"
                        val_match = re.search(r"[:\s]+(\d+(?:\.\d+)?)\s*([a-zA-Z%/\^0-9]+)?(?:\s+([0-9\.\-\s<>\(\)]+))?", text[match.end():])
                        if val_match:
                            raw_val = val_match.group(1)
                            raw_unit = val_match.group(2) or test_def["default_unit"]
                            raw_ref = val_match.group(3) or ""

                            # Ref low / high parsing if available
                            ref_low, ref_high = None, None
                            ref_range_match = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", raw_ref)
                            if ref_range_match:
                                try:
                                    ref_low = float(ref_range_match.group(1))
                                    ref_high = float(ref_range_match.group(2))
                                except ValueError:
                                    pass

                            numeric_v = float(raw_val)
                            provenance = ProvenanceRecord(
                                source_document_id=doc_id,
                                file_sha256=file_hash,
                                page_number=page,
                                line_number=line_no,
                                raw_text_snippet=text,
                            )

                            tests.append(ExtractedLabTest(
                                test_name=test_def["name"],
                                raw_value=raw_val,
                                numeric_value=numeric_v,
                                raw_unit=raw_unit,
                                reference_range_raw=raw_ref.strip() or None,
                                reference_low=ref_low,
                                reference_high=ref_high,
                                confidence=0.91,
                                provenance=provenance,
                            ))
                        break

        return tests

    def _extract_medications(self, ctx: PipelineContext, doc_id: str, file_hash: str) -> List[ExtractedMedication]:
        meds: List[ExtractedMedication] = []
        lines = ctx.ocr_lines

        for item in lines:
            text = item["text"]
            page = item["page"]
            line_no = item["line"]

            for drug in KNOWN_MEDICATION_NAMES:
                drug_match = re.search(rf"\b{drug}\b", text, re.I)
                if drug_match:
                    sub_text = text[drug_match.start():]
                    # Extract dose (e.g. 500 mg, 40mg) relative to drug position
                    dose_m = re.search(r"(\d+(?:\.\d+)?)\s*(mg|mcg|gm|ml|units)\b", sub_text, re.I)
                    dose_amt = dose_m.group(1) if dose_m else None
                    dose_u = dose_m.group(2) if dose_m else None


                    # Extract frequency (e.g. 1-0-1, OD, BD, TDS)
                    freq_m = re.search(r"\b(1-0-1|1-0-0|0-0-1|0-1-0|OD|BD|TDS|QID|once daily|twice daily|SOS)\b", text, re.I)
                    freq = freq_m.group(1) if freq_m else "OD"

                    # Duration
                    dur_m = re.search(r"(\d+\s*(?:days|weeks|months))", text, re.I)
                    duration = dur_m.group(1) if dur_m else None

                    provenance = ProvenanceRecord(
                        source_document_id=doc_id,
                        file_sha256=file_hash,
                        page_number=page,
                        line_number=line_no,
                        raw_text_snippet=text,
                    )

                    meds.append(ExtractedMedication(
                        drug_name=drug,
                        dose_amount=dose_amt,
                        dose_unit=dose_u,
                        frequency=freq,
                        duration=duration,
                        confidence=0.89,
                        provenance=provenance,
                    ))

        return meds

    def _extract_diagnoses(self, ctx: PipelineContext, doc_id: str, file_hash: str) -> List[ExtractedDiagnosis]:
        diagnoses: List[ExtractedDiagnosis] = []
        lines = ctx.ocr_lines

        patterns = [
            (r"(?:Type\s*2\s*Diabetes|T2DM|Diabetes\s*Mellitus)", "Type 2 Diabetes Mellitus"),
            (r"(?:Essential\s*Hypertension|Systemic\s*Hypertension|HTN\b)", "Essential Hypertension"),
            (r"(?:Dyslipidemia|Hyperlipidemia)", "Dyslipidemia"),
            (r"(?:Chronic\s*Kidney\s*Disease|CKD\b)", "Chronic Kidney Disease"),
            (r"(?:Ischemic\s*Heart\s*Disease|Coronary\s*Artery\s*Disease|CAD\b)", "Coronary Artery Disease"),
            (r"(?:Obesity\b)", "Obesity"),
        ]

        for item in lines:
            text = item["text"]
            for pat, name in patterns:
                if re.search(pat, text, re.I):
                    diag_type = "PRIMARY"
                    if "secondary" in text.lower() or "comorbid" in text.lower():
                        diag_type = "SECONDARY"
                    elif "provisional" in text.lower() or "impression" in text.lower():
                        diag_type = "PROVISIONAL"

                    provenance = ProvenanceRecord(
                        source_document_id=doc_id,
                        file_sha256=file_hash,
                        page_number=item["page"],
                        line_number=item["line"],
                        raw_text_snippet=text,
                    )

                    diagnoses.append(ExtractedDiagnosis(
                        diagnosis_name=name,
                        diagnosis_type=diag_type,
                        confidence=0.92,
                        provenance=provenance,
                    ))

        return diagnoses
