"""Stage 1: File Format Validation & Antivirus Guard.

Inspects raw byte headers, detects MIME inconsistencies, and performs malware
signature scanning (including EICAR standard tests and executable payload guards).
"""

import time
import hashlib
from typing import Tuple

from services.documents.pipeline.base import BasePipelineStage, PipelineContext, StageResult
from services.documents.models import IngestionStatus

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

MAGIC_NUMBERS = {
    "application/pdf": [b"%PDF-"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/tiff": [b"II*\x00", b"MM\x00*"],
    "image/webp": [b"RIFF"],
}

DISALLOWED_EXECUTABLE_SIGNATURES = [
    b"MZ",           # Windows PE executable / DLL
    b"\x7fELF",      # Linux ELF executable
    b"\xca\xfe\xba\xbe", # Java class or Mach-O binary
    b"#!/bin/sh",
    b"#!/bin/bash",
]


class VirusAndFileValidatorStage(BasePipelineStage):
    """Enforces zero-trust file safety, size limits, and malware scanning."""

    name = "VIRUS_FILE_VALIDATION"

    async def process(self, context: PipelineContext) -> StageResult:
        start_time = time.time()
        context.job.status = IngestionStatus.VALIDATING_FILE
        content = context.raw_content

        # 1. Size Validation
        if len(content) == 0:
            context.job.status = IngestionStatus.FAILED
            context.job.errors.append("Empty file uploaded (0 bytes)")
            return StageResult(
                stage_name=self.name,
                success=False,
                error="Empty file rejected",
                execution_seconds=time.time() - start_time,
            )

        if len(content) > MAX_FILE_SIZE_BYTES:
            context.job.status = IngestionStatus.FAILED
            context.job.errors.append(f"File size {len(content)} exceeds maximum limit of {MAX_FILE_SIZE_BYTES} bytes")
            return StageResult(
                stage_name=self.name,
                success=False,
                error="File size limit exceeded",
                execution_seconds=time.time() - start_time,
            )

        # 2. Antivirus & Malware Scan (EICAR & Executable Signatures)
        if EICAR_SIGNATURE in content:
            context.metadata.is_quarantined = True
            context.metadata.virus_scan_passed = False
            context.metadata.virus_scan_details = "EICAR Standard Antivirus Test Signature Detected"
            context.job.status = IngestionStatus.REJECTED
            context.job.errors.append("VIRUS_DETECTED: Document quarantined due to malicious signature.")
            return StageResult(
                stage_name=self.name,
                success=False,
                error="Malware signature identified in document payload",
                execution_seconds=time.time() - start_time,
            )

        for exe_sig in DISALLOWED_EXECUTABLE_SIGNATURES:
            if content.startswith(exe_sig):
                context.metadata.is_quarantined = True
                context.metadata.virus_scan_passed = False
                context.metadata.virus_scan_details = "Disallowed executable binary header disguised as medical document"
                context.job.status = IngestionStatus.REJECTED
                context.job.errors.append("SECURITY_VIOLATION: Executable payload header detected.")
                return StageResult(
                    stage_name=self.name,
                    success=False,
                    error="Disallowed executable file type detected",
                    execution_seconds=time.time() - start_time,
                )

        # 3. Magic Number & MIME Byte Sniffing
        declared_mime = context.metadata.content_type.lower()
        if declared_mime in MAGIC_NUMBERS:
            expected_magics = MAGIC_NUMBERS[declared_mime]
            matched = any(content.startswith(mag) for mag in expected_magics)
            if not matched and declared_mime == "application/pdf":
                # PDF header might be within first 1024 bytes
                matched = b"%PDF-" in content[:1024]

            if not matched:
                context.job.status = IngestionStatus.FAILED
                err = f"MIME mismatch: declared '{declared_mime}' does not match file byte magic headers"
                context.job.errors.append(err)
                return StageResult(
                    stage_name=self.name,
                    success=False,
                    error=err,
                    execution_seconds=time.time() - start_time,
                )

        # Check hash match
        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != context.metadata.sha256_hash:
            context.job.status = IngestionStatus.FAILED
            err = "Checksum integrity violation: payload hash does not match metadata"
            context.job.errors.append(err)
            return StageResult(
                stage_name=self.name,
                success=False,
                error=err,
                execution_seconds=time.time() - start_time,
            )

        context.metadata.virus_scan_passed = True
        context.metadata.virus_scan_details = "Passed file format inspection & malware heuristics"
        elapsed = time.time() - start_time
        context.job.pipeline_stage_timings[self.name] = elapsed

        return StageResult(
            stage_name=self.name,
            success=True,
            message="Virus scan and file format validation passed",
            execution_seconds=elapsed,
        )
