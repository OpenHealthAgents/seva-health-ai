"""Comprehensive Test Suite for Security Hardening (PROMPT 23).

Verifies:
1. Secure HTTP headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Cache-Control).
2. Sliding-window rate limiting (HTTP 429 Too Many Requests & Retry-After).
3. Input sanitization & XSS neutralization.
4. Server-Side Request Forgery (SSRF) defense against internal/private IP targets.
5. Secure file validation (magic bytes, path traversal sanitization, executable detection).
6. Authenticated field-level encryption at rest (AES-256-GCM) & tamper detection.
"""

import pytest
from starlette.testclient import TestClient

from services.api.main import app
from packages.security.headers import SecureHeadersMiddleware
from packages.security.rate_limiter import rate_limiter, SlidingWindowRateLimiter
from packages.security.validation import InputSanitizer, SSRFGuard, SSRFViolationError
from packages.security.file_validator import SecureFileValidator, FileValidationError
from packages.security.encryption import AESGCMFieldEncryption, EncryptionError

client = TestClient(app)


# ==============================================================================
# 1. Secure HTTP Headers Verification
# ==============================================================================

def test_secure_headers_injected_on_responses():
    """All HTTP responses must carry hardened security headers."""
    res = client.get("/health")
    assert res.status_code == 200

    # Verify standard OWASP / HIPAA security headers
    assert "Content-Security-Policy" in res.headers
    assert "default-src 'self'" in res.headers["Content-Security-Policy"]
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Strict-Transport-Security" in res.headers
    assert "max-age=31536000" in res.headers["Strict-Transport-Security"]
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in res.headers


def test_sensitive_routes_enforce_no_cache():
    """Sensitive clinical, auth, and privacy endpoints must strictly forbid client caching."""
    sensitive_paths = [
        "/api/v1/auth/sessions",
        "/api/v1/citizens",
        "/api/v1/risk/models",
        "/api/v1/privacy/consents",
    ]

    for path in sensitive_paths:
        res = client.get(path)
        # Even if unauthorized (401/403), the headers must prohibit caching
        assert "Cache-Control" in res.headers
        assert "no-store" in res.headers["Cache-Control"]
        assert "no-cache" in res.headers["Cache-Control"]


# ==============================================================================
# 2. Sliding-Window Rate Limiting Verification
# ==============================================================================

def test_rate_limiter_blocks_excess_requests():
    """Rate limiter enforces quota and returns HTTP 429 when requests exceed threshold."""
    custom_limiter = SlidingWindowRateLimiter(window_seconds=10)
    custom_limiter.limits["default"] = 5  # Allow max 5 requests

    client_key = "test-client-ip-001"
    path = "/api/v1/test-route"

    # First 5 requests must be permitted
    for i in range(5):
        allowed, remaining, limit = custom_limiter.is_allowed(client_key, path)
        assert allowed is True
        assert remaining == 5 - (i + 1)

    # 6th request must be rejected
    allowed, remaining, limit = custom_limiter.is_allowed(client_key, path)
    assert allowed is False
    assert remaining == 0


def test_rate_limiter_middleware_http_429():
    """Live API client receives standard HTTP 429 Too Many Requests when rate limit is exceeded."""
    # Temporarily lower the limit for testing
    original_limit = rate_limiter.limits["auth"]
    rate_limiter.limits["auth"] = 3
    rate_limiter.reset()

    try:
        # Send 3 rapid requests to /api/v1/auth/token
        for _ in range(3):
            client.post("/api/v1/auth/token", json={"email": "bad@seva.ai", "password": "wrong"})

        # 4th request must trigger HTTP 429
        res_blocked = client.post("/api/v1/auth/token", json={"email": "bad@seva.ai", "password": "wrong"})
        assert res_blocked.status_code == 429
        body = res_blocked.json()
        assert "Rate limit exceeded" in body["detail"]
        assert "Retry-After" in res_blocked.headers
        assert res_blocked.headers["X-RateLimit-Remaining"] == "0"
    finally:
        # Restore normal rate limits
        rate_limiter.limits["auth"] = original_limit
        rate_limiter.reset()


# ==============================================================================
# 3. Input Sanitization & XSS Neutralization
# ==============================================================================

def test_xss_detection_and_sanitization():
    """InputSanitizer detects malicious script tags and strips executable vectors."""
    malicious_inputs = [
        ("<script>alert('XSS')</script>", "alert(&#x27;XSS&#x27;)"),
        ("<iframe src='javascript:alert(1)'></iframe>", ""),
        ("<img src=x onerror=alert('cookie')>", "&lt;img src=x&gt;"),
        ("Normal Clinical Notes for Ramesh", "Normal Clinical Notes for Ramesh"),
    ]

    for attack, expected_clean in malicious_inputs:
        cleaned = InputSanitizer.sanitize_text(attack)
        assert "<script>" not in cleaned
        assert "javascript:" not in cleaned
        assert "onerror=" not in cleaned

    # Check detector
    assert InputSanitizer.check_for_xss("<script>steal()</script>") is True
    assert InputSanitizer.check_for_xss("<img src=x onload=evil()>") is True
    assert InputSanitizer.check_for_xss("Normal blood pressure 120/80") is False


# ==============================================================================
# 4. Server-Side Request Forgery (SSRF) Defense
# ==============================================================================

def test_ssrf_blocks_private_and_cloud_metadata_ips():
    """SSRFGuard strictly blocks internal networks, localhost, and cloud metadata targets."""
    prohibited_targets = [
        "http://127.0.0.1:8000/internal",
        "http://localhost:6379",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/admin",
        "http://192.168.1.1/router",
        "http://172.16.0.5:9000",
        "file:///etc/passwd",
        "ftp://internal.sevahealth.local",
    ]

    for target in prohibited_targets:
        with pytest.raises(SSRFViolationError):
            SSRFGuard.validate_url(target)

    # Valid external public URL must be permitted
    valid_url = "https://abdm.gov.in/api/v1/health-info"
    assert SSRFGuard.validate_url(valid_url) == valid_url


# ==============================================================================
# 5. Secure File Validation & Path Traversal Prevention
# ==============================================================================

def test_filename_sanitization_blocks_path_traversal():
    """SecureFileValidator strips directory traversal sequences and null bytes."""
    traversal_filenames = [
        ("../../etc/passwd", "etc_passwd"),
        ("..\\..\\windows\\system32\\cmd.exe", "windows_system32_cmd.exe"),
        ("report/../../secret.pdf", "secret.pdf"),
    ]

    for malicious_name, expected_base in traversal_filenames:
        clean = SecureFileValidator.sanitize_filename(malicious_name)
        assert ".." not in clean
        assert "/" not in clean
        assert "\\" not in clean

    # Null byte attack must be rejected
    with pytest.raises(FileValidationError):
        SecureFileValidator.sanitize_filename("report.pdf\x00.exe")


def test_file_magic_bytes_and_executable_rejection():
    """SecureFileValidator verifies true content magic bytes and rejects disguised executables."""
    # 1. Valid PDF with %PDF- header
    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    name, ext = SecureFileValidator.validate_file("lab_report.pdf", valid_pdf_content)
    assert ext == ".pdf"

    # 2. Executable disguised as PDF (MZ header)
    disguised_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    with pytest.raises(FileValidationError, match="executable"):
        SecureFileValidator.validate_file("fake_report.pdf", disguised_exe)

    # 3. Extension mismatch (plain text with .png extension)
    fake_png = b"Hello I am just plain text"
    with pytest.raises(FileValidationError, match="magic bytes do not match"):
        SecureFileValidator.validate_file("image.png", fake_png)

    # 4. Prohibited file extension (.exe, .sh)
    with pytest.raises(FileValidationError, match="Prohibited file extension"):
        SecureFileValidator.validate_file("script.sh", b"#!/bin/bash\necho hack")


# ==============================================================================
# 6. Field-Level Encryption at Rest (AES-256-GCM)
# ==============================================================================

def test_aes_gcm_field_level_encryption_at_rest():
    """AESGCMFieldEncryption encrypts, decrypts, and rejects tampered ciphertext."""
    encryptor = AESGCMFieldEncryption(key_material="super-secret-production-encryption-key-32chars")
    sensitive_phi = "ABHA: 91-4829-1029-4820 | Diagnosis: Pre-diabetes"

    # Encrypt
    ciphertext = encryptor.encrypt(sensitive_phi)
    assert ciphertext != sensitive_phi
    assert len(ciphertext) > len(sensitive_phi)

    # Decrypt
    decrypted = encryptor.decrypt(ciphertext)
    assert decrypted == sensitive_phi

    # Tamper detection (modified ciphertext byte)
    tampered = ciphertext[:-4] + "AAAA"
    with pytest.raises(EncryptionError):
        encryptor.decrypt(tampered)
