"""Secure File Validator, Malware Signature Scanner & Path Traversal Guard.

Defends against:
1. Path traversal attacks (escaping storage root via ../ or null bytes).
2. Malicious document uploads (renamed executables, polyglots, script files).
3. MIME confusion & magic byte mismatches.
4. Denial of service via oversized files.
"""

import os
import re
from typing import Tuple, Set


class FileValidationError(Exception):
    """Raised when an uploaded file fails security validation."""
    pass


class SecureFileValidator:
    """Rigorous file security validator for clinical documents and lab reports."""

    MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
    ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".png", ".jpg", ".jpeg"}

    # Magic byte signatures
    MAGIC_SIGNATURES = {
        ".pdf": [b"%PDF-"],
        ".png": [b"\x89PNG\r\n\x1a\n"],
        ".jpg": [b"\xff\xd8\xff"],
        ".jpeg": [b"\xff\xd8\xff"],
    }

    # Prohibited executable headers
    DANGEROUS_SIGNATURES = [
        (b"MZ", "Windows PE / EXE executable"),
        (b"\x7fELF", "Linux ELF executable"),
        (b"PK\x03\x04", "ZIP / Jar container (potential disguised archive)"),  # PDFs should not be raw zip
        (b"#!", "Shell script shebang"),
    ]

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Strips directory traversal sequences, null bytes, and dangerous characters.
        Guarantees filename is a safe basename.
        """
        if not filename or not isinstance(filename, str):
            return "uploaded_document"

        # Check for null byte attacks
        if "\x00" in filename:
            raise FileValidationError("Null byte injection detected in filename.")

        # Check for directory traversal sequences
        if ".." in filename or "/" in filename or "\\" in filename:
            # Strip path elements to retain only base name
            clean_name = os.path.basename(filename.replace("\\", "/"))
        else:
            clean_name = filename

        # Keep only alphanumeric characters, underscores, dashes, and single period
        safe_name = re.sub(r"[^\w\.\-]", "_", clean_name)
        if not safe_name or safe_name.startswith("."):
            safe_name = f"doc_{safe_name.lstrip('.')}"

        return safe_name

    @classmethod
    def validate_file(cls, filename: str, content: bytes) -> Tuple[str, str]:
        """Performs full security audit on filename and raw byte contents.
        Returns: (safe_filename, detected_extension)
        """
        if not content or len(content) == 0:
            raise FileValidationError("Empty file uploaded. Content size is 0 bytes.")

        if len(content) > cls.MAX_FILE_SIZE_BYTES:
            raise FileValidationError(
                f"File size exceeds maximum permitted limit ({len(content)/(1024*1024):.1f} MB > 15.0 MB)."
            )

        safe_name = cls.sanitize_filename(filename)
        _, ext = os.path.splitext(safe_name.lower())

        if ext not in cls.ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"Prohibited file extension '{ext}'. Only {list(cls.ALLOWED_EXTENSIONS)} are permitted."
            )

        # 1. Dangerous signature audit (Reject disguised executables)
        for sig, description in cls.DANGEROUS_SIGNATURES:
            if content.startswith(sig) and ext == ".pdf" and sig != b"%PDF-":
                raise FileValidationError(f"Malicious file signature detected: {description}.")

        # 2. Magic byte verification
        expected_sigs = cls.MAGIC_SIGNATURES.get(ext, [])
        matches_magic = any(content.startswith(sig) for sig in expected_sigs)
        if not matches_magic:
            raise FileValidationError(
                f"File content magic bytes do not match declared extension '{ext}'."
            )

        return safe_name, ext
