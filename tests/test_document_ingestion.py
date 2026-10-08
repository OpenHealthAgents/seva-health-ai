"""Comprehensive Test Suite for Clinical Document Ingestion Subsystem.

Verifies:
1. Inputs: PDF, PNG/JPEG images, Lab reports, Prescriptions, Discharge summaries, Health packages.
2. 10-Stage Pipeline:
   UPLOAD -> VIRUS/FILE VALIDATION -> DOCUMENT CLASSIFICATION -> OCR ->
   EXTRACTION -> NORMALIZATION -> VALIDATION -> CLINICAL MAPPING ->
   HUMAN REVIEW -> CLINICAL RECORD.
3. Extracted Entities:
   - patient identifiers (Name, ABHA ID, Age, Gender, MRN)
   - test names, values, units, reference ranges
   - dates (report date, specimen date, prescription date, admission, discharge)
   - medications (drug name, dose, frequency, duration)
   - diagnoses (primary, secondary)
   - provider (doctor name, registration number)
   - facility (hospital/lab name, accreditation)
4. Critical Invariants:
   - Never automatically commit uncertain extracted clinical values without validation.
   - Preserve original document bytes and verify cryptographic SHA-256 hash.
   - Store provenance (doc ID, SHA-256, page, line, snippet).
   - Store extraction confidence per field and overall.
   - Human review required for low-confidence (< 0.85) or invalid fields.
"""

import io
import hashlib
import pytest
from PIL import Image
from starlette.testclient import TestClient

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload, create_access_token
from services.api.main import app
from services.store import store
from scripts.seed_data import seed_all_demo_data
from services.documents.models import (
    DocumentType,
    IngestionStatus,
    FieldReviewStatus,
    HumanReviewCorrection,
)
from services.documents.engine import ingestion_engine

client = TestClient(app)


def build_synthetic_pdf(text_lines: list) -> bytes:
    """Builds a valid multi-line PDF byte stream for testing."""
    escaped = "\n".join(text_lines).replace("(", "\\(").replace(")", "\\)")
    stream_content = f"BT /F1 12 Tf 72 712 Td ({escaped}) Tj ET"
    stream_bytes = stream_content.encode("latin-1")

    return (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>>>>> /MediaBox [0 0 612 792] /Contents 4 0 R>> endobj\n"
        b"4 0 obj <</Length " + str(len(stream_bytes)).encode() + b">> stream\n"
        + stream_bytes +
        b"\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000281 00000 n \ntrailer <</Size 5 /Root 1 0 R>>\nstartxref\n380\n%%EOF"
    )


def build_synthetic_png() -> bytes:
    """Builds a valid PNG image byte stream."""
    img = Image.new("RGB", (300, 150), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def setup_seed():
    """Ensure clean store before each test."""
    store.document_files.clear()
    store.ingestion_jobs.clear()
    store.review_queue.clear()
    store.legal_clinical_records.clear()
    seed_all_demo_data()


@pytest.fixture
def doctor_actor():
    return TokenPayload(
        sub="doctor-user-01",
        tenant_id="karnataka_state_health",
        role=UserRole.CLINICIAN,
    )


@pytest.fixture
def citizen_actor():
    return TokenPayload(
        sub="citizen-user-01",
        tenant_id="karnataka_state_health",
        role=UserRole.CITIZEN,
    )


# ==============================================================================
# 1. FILE & VIRUS VALIDATION TESTS
# ==============================================================================

class TestFileValidationAndVirusGuard:
    """Verifies file headers, MIME byte-sniffing, and antivirus protections."""

    @pytest.mark.asyncio
    async def test_reject_empty_file(self):
        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=b"",
            filename="empty.pdf",
            content_type="application/pdf",
            title="Empty File",
            uploader_id="tester",
        )
        assert job.status == IngestionStatus.FAILED
        assert any("Empty file" in err for err in job.errors)

    @pytest.mark.asyncio
    async def test_detect_eicar_virus_signature(self):
        eicar_payload = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=eicar_payload,
            filename="infected_report.pdf",
            content_type="application/pdf",
            title="Infected Lab Report",
            uploader_id="tester",
        )
        assert job.status == IngestionStatus.REJECTED
        assert any("VIRUS_DETECTED" in err for err in job.errors)

    @pytest.mark.asyncio
    async def test_reject_disguised_executable(self):
        # Disguised Windows PE binary starting with MZ
        fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00malicious_binary_content"
        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=fake_pdf,
            filename="report.pdf",
            content_type="application/pdf",
            title="Executable Disguised as PDF",
            uploader_id="tester",
        )
        assert job.status == IngestionStatus.REJECTED
        assert any("SECURITY_VIOLATION" in err for err in job.errors)

    @pytest.mark.asyncio
    async def test_mime_mismatch_detection(self):
        # Declared as PDF but given arbitrary non-PDF bytes
        invalid_pdf = b"NOT_A_VALID_PDF_HEADER_AT_ALL"
        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=invalid_pdf,
            filename="corrupt.pdf",
            content_type="application/pdf",
            title="Corrupted File",
            uploader_id="tester",
        )
        assert job.status == IngestionStatus.FAILED
        assert any("MIME mismatch" in err for err in job.errors)


# ==============================================================================
# 2. DOCUMENT CLASSIFICATION & OCR TESTS
# ==============================================================================

class TestDocumentClassificationAndOCR:
    """Verifies multi-type document classification and OCR line parsing."""

    @pytest.mark.asyncio
    async def test_classify_lab_report(self):
        pdf_bytes = build_synthetic_pdf([
            "Karnataka Diagnostic Centre",
            "Investigation Report - Bio-Chemistry & Hematology",
            "Test Name Observed Value Reference Range",
            "Fasting Blood Glucose 134.0 mg/dL 70 - 100",
        ])
        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=pdf_bytes,
            filename="blood_investigation.pdf",
            content_type="application/pdf",
            title="Comprehensive Laboratory Investigation",
            uploader_id="tester",
        )
        assert job.document_type == DocumentType.LAB_REPORT
        assert job.classification_confidence >= 0.70
        assert job.ocr_pages_count >= 1

    @pytest.mark.asyncio
    async def test_classify_prescription(self):
        pdf_bytes = build_synthetic_pdf([
            "Dr. Ramesh Kumar MD - Consultation Rx",
            "Prescription Details",
            "Tab. Metformin 500 mg 1-0-1 after food for 30 days",
            "Tab. Telmisartan 40 mg 1-0-0 before food",
        ])
        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=pdf_bytes,
            filename="rx_card.pdf",
            content_type="application/pdf",
            title="Physician Prescription Rx",
            uploader_id="tester",
        )
        assert job.document_type == DocumentType.PRESCRIPTION
        assert job.classification_confidence >= 0.70

    @pytest.mark.asyncio
    async def test_classify_discharge_summary(self):
        pdf_bytes = build_synthetic_pdf([
            "Mysuru District Hospital",
            "Discharge Summary",
            "Date of Admission: 2026-09-28",
            "Date of Discharge: 2026-10-02",
            "Hospital Course and Condition on Discharge: Stable",
        ])
        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=pdf_bytes,
            filename="discharge_note.pdf",
            content_type="application/pdf",
            title="Inpatient Discharge Summary",
            uploader_id="tester",
        )
        assert job.document_type == DocumentType.DISCHARGE_SUMMARY

    @pytest.mark.asyncio
    async def test_image_ocr_ingestion(self):
        png_bytes = build_synthetic_png()
        mock_text = (
            "Karnataka Diagnostic Centre\n"
            "Patient Name: Ramesh Patel Age: 48 Yrs Gender: Male\n"
            "HbA1c: 6.8 % 4.0 - 5.6\n"
            "Serum Creatinine: 1.2 mg/dL 0.7 - 1.2\n"
        )
        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=png_bytes,
            filename="scan_lab.png",
            content_type="image/png",
            title="Scanned Lab Report Image",
            uploader_id="tester",
            mock_ocr_text=mock_text,
        )
        assert job.ocr_pages_count == 1
        assert len(job.extractions.tests) >= 2


# ==============================================================================
# 3. EXTRACTION, NORMALIZATION, VALIDATION & MAPPING TESTS
# ==============================================================================

class TestClinicalExtractionPipeline:
    """Verifies extraction of all 10 required items, normalization, validation, and mapping."""

    @pytest.mark.asyncio
    async def test_full_clinical_entity_extraction(self):
        doc_lines = [
            "Facility: Karnataka Diagnostic Centre NABL Accredited",
            "Patient Name: Ramesh Patel",
            "ABHA ID: 91-4829-1029-4820",
            "Age: 48 Yrs Gender: MALE MRN: 482910",
            "Report Date: 04/10/2026",
            "Doctor: Dr. Ramesh Kumar MD Reg No: KMC-49281",
            "Primary Diagnosis: Type 2 Diabetes Mellitus",
            "Fasting Blood Glucose 134.0 mg/dl 70 - 100",
            "HbA1c 6.8 % 4.0 - 5.6",
            "Serum Creatinine 1.2 mg/dl 0.7 - 1.2",
            "Systolic BP 138 mmhg 90 - 120",
            "Tab. Metformin 500 mg 1-0-1 30 days",
        ]
        pdf_bytes = build_synthetic_pdf(doc_lines)

        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=pdf_bytes,
            filename="comprehensive_report.pdf",
            content_type="application/pdf",
            title="Comprehensive Metabolic Panel",
            uploader_id="tester",
        )
        bundle = job.extractions

        # 1. Patient Identifiers
        assert bundle.patient.patient_name == "Ramesh Patel"
        assert bundle.patient.abha_id == "91-4829-1029-4820"
        assert bundle.patient.age == 48
        assert bundle.patient.gender == "MALE"
        assert bundle.patient.mrn_or_patient_id == "482910"

        # 2. Test Names, Values, Normalized Units, Reference Ranges
        test_names = [t.canonical_name for t in bundle.tests]
        assert "Fasting Blood Glucose" in test_names
        assert "HbA1c" in test_names
        assert "Serum Creatinine" in test_names
        assert "Systolic Blood Pressure" in test_names

        fbs = next(t for t in bundle.tests if t.canonical_name == "Fasting Blood Glucose")
        assert fbs.numeric_value == 134.0
        assert fbs.normalized_unit == "mg/dL"  # Unit normalization from mg/dl
        assert fbs.interpretation == "HIGH"
        assert fbs.reference_low == 70.0
        assert fbs.reference_high == 100.0

        # 3. Clinical Terminology Mapping (LOINC)
        assert fbs.loinc_code == "1558-6"
        hba1c = next(t for t in bundle.tests if t.canonical_name == "HbA1c")
        assert hba1c.loinc_code == "4548-4"

        # 4. Dates Normalization
        assert bundle.dates.report_date == "2026-10-04"  # ISO-8601 normalization

        # 5. Medications & RxNorm Mapping
        assert len(bundle.medications) >= 1
        med = bundle.medications[0]
        assert med.drug_name == "Metformin"
        assert med.dose_amount == "500"
        assert med.dose_unit == "mg"
        assert med.frequency == "1-0-1"
        assert med.rxnorm_code == "6809"

        # 6. Diagnoses & SNOMED CT Mapping
        assert len(bundle.diagnoses) >= 1
        diag = bundle.diagnoses[0]
        assert diag.diagnosis_name == "Type 2 Diabetes Mellitus"
        assert diag.snomed_ct_code == "44054006"
        assert diag.icd10_code == "E11.9"

        # 7. Provider & Facility
        assert bundle.provider.doctor_name == "Dr. Ramesh Kumar"
        assert bundle.provider.registration_number == "KMC-49281"
        assert bundle.facility.accreditation == "NABL"

    @pytest.mark.asyncio
    async def test_physiological_out_of_bounds_validation(self):
        # Impossible biological value: HbA1c 85%
        doc_lines = [
            "Patient Name: Ramesh Patel",
            "HbA1c 85.0 % 4.0 - 5.6",
        ]
        pdf_bytes = build_synthetic_pdf(doc_lines)

        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=pdf_bytes,
            filename="invalid_hba1c.pdf",
            content_type="application/pdf",
            title="Biologically Impossible Lab",
            uploader_id="tester",
        )

        test = job.extractions.tests[0]
        assert test.is_valid_physiological is False
        assert any("Physiological Out-of-Bounds" in flag for flag in test.validation_flags)
        assert job.requires_human_review is True
        assert job.status == IngestionStatus.HUMAN_REVIEW_REQUIRED


# ==============================================================================
# 4. HUMAN REVIEW GATE & CLINICAL RECORD COMMITTER TESTS
# ==============================================================================

class TestHumanReviewAndSafetyInvariants:
    """Verifies that unvalidated uncertain values are NEVER automatically committed."""

    @pytest.mark.asyncio
    async def test_uncertain_values_gate_legal_record(self):
        # A document with physiological out-of-bounds trigger
        doc_lines = [
            "Patient Name: Ramesh Patel",
            "Fasting Blood Glucose 950.0 mg/dL 70 - 100",  # Physiological out of bounds (> 800)
        ]
        pdf_bytes = build_synthetic_pdf(doc_lines)
        cid = "citizen-ramesh-patel-01"

        init_obs_count = len(store.observations.get(cid, []))
        init_legal_count = len(store.legal_clinical_records.get(cid, []))

        job = await ingestion_engine.ingest_document(
            citizen_id=cid,
            file_content=pdf_bytes,
            filename="unvalidated.pdf",
            content_type="application/pdf",
            title="Unvalidated Document",
            uploader_id="tester",
        )

        # Invariant Verification
        assert job.status == IngestionStatus.HUMAN_REVIEW_REQUIRED
        assert job.requires_human_review is True
        assert len(job.committed_observation_ids) == 0
        assert job.committed_legal_record_id is None

        # Zero observations written to legal record
        assert len(store.observations.get(cid, [])) == init_obs_count
        assert len(store.legal_clinical_records.get(cid, [])) == init_legal_count
        assert job.job_id in store.review_queue

    @pytest.mark.asyncio
    async def test_clinician_human_review_and_committal(self):
        doc_lines = [
            "Patient Name: Ramesh Patel",
            "Fasting Blood Glucose 950.0 mg/dL 70 - 100",
        ]
        pdf_bytes = build_synthetic_pdf(doc_lines)
        cid = "citizen-ramesh-patel-01"

        job = await ingestion_engine.ingest_document(
            citizen_id=cid,
            file_content=pdf_bytes,
            filename="pending_review.pdf",
            content_type="application/pdf",
            title="Pending Review Report",
            uploader_id="tester",
        )
        assert job.status == IngestionStatus.HUMAN_REVIEW_REQUIRED
        target_test_id = job.extractions.tests[0].id

        # Clinician corrects the transcription typo: 950 -> 150 mg/dL
        correction = HumanReviewCorrection(
            action="CORRECT",
            target_category="TEST",
            target_id=target_test_id,
            corrected_value=150.0,
            corrected_unit="mg/dL",
            corrected_interpretation="HIGH",
            reviewer_notes="OCR error: corrected digit 9 to 1. True value is 150 mg/dL.",
            reviewer_id="doctor-user-01",
            reviewer_name="Dr. Verified Clinician",
        )

        updated_job = await ingestion_engine.apply_human_review(
            job_id=job.job_id,
            corrections=[correction],
            reviewer_id="doctor-user-01",
            reviewer_name="Dr. Verified Clinician",
        )

        # Verified & Committed State
        assert updated_job.status == IngestionStatus.COMMITTED_TO_CLINICAL_RECORD
        assert updated_job.requires_human_review is False
        assert len(updated_job.committed_observation_ids) == 1
        assert updated_job.committed_legal_record_id is not None

        # Record is now in store.observations and store.legal_clinical_records
        citizen_obs = store.observations[cid]
        new_obs = next(o for o in citizen_obs if o.id == updated_job.committed_observation_ids[0])
        assert new_obs.value == 150.0
        assert new_obs.unit == "mg/dL"
        assert new_obs.is_abnormal is True

        legal_recs = store.legal_clinical_records[cid]
        assert any(r["record_id"] == updated_job.committed_legal_record_id for r in legal_recs)

        # Dequeued from review queue
        assert job.job_id not in store.review_queue


# ==============================================================================
# 5. ORIGINAL DOCUMENT PRESERVATION & PROVENANCE TESTS
# ==============================================================================

class TestPreservationAndProvenance:
    """Verifies raw document immutable preservation, hashing, and field-level provenance."""

    @pytest.mark.asyncio
    async def test_original_document_preservation(self):
        pdf_bytes = build_synthetic_pdf([
            "Patient Name: Ramesh Patel",
            "HbA1c 6.5 % 4.0 - 5.6",
        ])
        expected_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        job = await ingestion_engine.ingest_document(
            citizen_id="citizen-ramesh-patel-01",
            file_content=pdf_bytes,
            filename="original_preserve.pdf",
            content_type="application/pdf",
            title="Preservation Test Document",
            uploader_id="tester",
        )

        doc_record = store.document_files.get(job.document_id)
        assert doc_record is not None
        assert doc_record["sha256_hash"] == expected_sha256
        assert doc_record["raw_bytes"] == pdf_bytes  # Exact byte-for-byte preservation

        # Provenance on extracted test
        test = job.extractions.tests[0]
        assert test.provenance is not None
        assert test.provenance.source_document_id == job.document_id
        assert test.provenance.file_sha256 == expected_sha256
        assert test.provenance.page_number >= 1
        assert "HbA1c" in test.provenance.raw_text_snippet


# ==============================================================================
# 6. REST API INTEGRATION TESTS
# ==============================================================================

class TestClinicalDocumentRESTEndpoints:
    """Verifies all FastAPI routes for document ingestion, review queue, and download."""

    def test_api_ingest_document(self, doctor_actor):
        token = create_access_token(
            subject=doctor_actor.sub,
            tenant_id=doctor_actor.tenant_id,
            role=doctor_actor.role,
        )
        pdf_bytes = build_synthetic_pdf([
            "Karnataka Diagnostic Centre",
            "Patient Name: Ramesh Patel",
            "Fasting Blood Glucose 124.0 mg/dL 70 - 100",
        ])

        resp = client.post(
            "/api/v1/documents/ingest",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "citizen_id": "citizen-ramesh-patel-01",
                "title": "API Metabolic Panel",
            },
            files={
                "file": ("metabolic.pdf", pdf_bytes, "application/pdf")
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["document_id"] != ""
        assert len(data["extractions"]["tests"]) >= 1

    def test_api_get_review_queue_and_submit_review(self, doctor_actor):
        token = create_access_token(
            subject=doctor_actor.sub,
            tenant_id=doctor_actor.tenant_id,
            role=doctor_actor.role,
        )

        # 1. Ingest document requiring review
        pdf_bytes = build_synthetic_pdf([
            "Patient Name: Ramesh Patel",
            "Fasting Blood Glucose 980.0 mg/dL 70 - 100",  # Out of bounds
        ])
        ingest_resp = client.post(
            "/api/v1/documents/ingest",
            headers={"Authorization": f"Bearer {token}"},
            data={"citizen_id": "citizen-ramesh-patel-01", "title": "Queue Test"},
            files={"file": ("queue_test.pdf", pdf_bytes, "application/pdf")},
        )
        assert ingest_resp.status_code == 200
        job_data = ingest_resp.json()
        job_id = job_data["job_id"]
        test_id = job_data["extractions"]["tests"][0]["id"]

        # 2. Check review queue endpoint
        q_resp = client.get(
            "/api/v1/documents/review-queue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert q_resp.status_code == 200
        queue_items = q_resp.json()
        assert any(item["job_id"] == job_id for item in queue_items)

        # 3. Submit Clinician Review
        review_payload = {
            "corrections": [
                {
                    "action": "CORRECT",
                    "target_category": "TEST",
                    "target_id": test_id,
                    "corrected_value": 128.0,
                    "corrected_unit": "mg/dL",
                    "corrected_interpretation": "HIGH",
                    "reviewer_notes": "Corrected laboratory value to 128.0 mg/dL",
                    "reviewer_id": doctor_actor.sub,
                    "reviewer_name": "Dr. Ramesh Kumar",
                }
            ]
        }
        rev_resp = client.post(
            f"/api/v1/documents/jobs/{job_id}/human-review",
            headers={"Authorization": f"Bearer {token}"},
            json=review_payload,
        )
        assert rev_resp.status_code == 200
        rev_data = rev_resp.json()
        assert rev_data["status"] == "COMMITTED_TO_CLINICAL_RECORD"
        assert len(rev_data["committed_observation_ids"]) == 1

    def test_api_download_preserved_document(self, doctor_actor):
        token = create_access_token(
            subject=doctor_actor.sub,
            tenant_id=doctor_actor.tenant_id,
            role=doctor_actor.role,
        )
        pdf_bytes = build_synthetic_pdf(["Original Preserved Content"])
        sha256_expected = hashlib.sha256(pdf_bytes).hexdigest()

        ingest_resp = client.post(
            "/api/v1/documents/ingest",
            headers={"Authorization": f"Bearer {token}"},
            data={"citizen_id": "citizen-ramesh-patel-01", "title": "Download Test"},
            files={"file": ("preserve.pdf", pdf_bytes, "application/pdf")},
        )
        doc_id = ingest_resp.json()["document_id"]

        # Download original
        dl_resp = client.get(
            f"/api/v1/documents/download/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dl_resp.status_code == 200
        assert dl_resp.content == pdf_bytes
        assert dl_resp.headers.get("x-sha256-checksum") == sha256_expected
