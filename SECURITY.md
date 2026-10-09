# Security Policy: SevaHealth AI Platform

## 1. Overview & Commitment to Healthcare Security

**SevaHealth AI** is designed with a **Zero-Trust, Security-by-Design** posture. Because our platform processes sensitive biometric vitals, longitudinal clinical observations, wearable telemetry, and citizen identity attributes (such as ABHA IDs), we enforce the highest standards of data confidentiality, integrity, availability, and clinical safety.

Our security framework strictly complies with:
- **Digital Personal Data Protection Act (DPDP Act 2023 - India)**
- **Digital Information Security in Healthcare Act (DISHA - India)**
- **Ayushman Bharat Digital Mission (ABDM) Data Privacy & Security Policies**
- **HIPAA Security & Privacy Rules (45 CFR Part 160 and Part 164)**
- **ISO/IEC 27001 Information Security Management**
- **OWASP Top 10 & OWASP Top 10 for Large Language Model Applications (LLM01-LLM10)**

---

## 2. Supported Versions

Security updates, vulnerability patches, and emergency fixes are applied to the following active release branches:

| Version | Status | Supported | Security Patch Window |
| :--- | :--- | :--- | :--- |
| **v1.0.x** | Current Production Release | :white_check_mark: Yes | Immediate (< 24 hours for Critical/High) |
| **v0.9.x** | Pre-Release / Pilot | :white_check_mark: Yes | Standard (< 72 hours) |
| **< v0.9.0** | Deprecated Alpha | :x: No | Unsupported |

---

## 3. Reporting a Vulnerability

We welcome coordinated vulnerability disclosures (CVD) from independent security researchers, clinical partners, and healthcare organizations.

### Reporting Channel
- **Email:** `security@sevahealth.ai`
- **PGP Encryption Key:** Fingerprint `4A9F 1B8C 9E21 70DA E432  9F23 881B 6620 901E 55A1`
- **Subject Format:** `[SECURITY DISCLOSURE] - <Brief Summary of Issue>`

### Reporting Guidelines
When reporting a security finding, please provide:
1. Description of the vulnerability and attack vector.
2. Steps to reproduce or proof-of-concept (non-destructive).
3. Potential impact on Protected Health Information (PHI) or clinical operations.
4. Any potential mitigations or remediation suggestions.

### Our Response SLA
- **Initial Acknowledgment:** Within **24 hours**.
- **Triage & Severity Assessment:** Within **48 hours**.
- **Remediation & Patch Deployment:**
  - *Critical (CVSS 9.0–10.0 / PHI Breach / RCE):* **24–48 hours**
  - *High (CVSS 7.0–8.9 / Priv Escalation / SSRF / IDOR):* **72 hours**
  - *Medium / Low (CVSS < 7.0):* Next scheduled sprint release (within 7–14 days)
- **Safe Harbor:** We will not pursue legal action against researchers who discover vulnerabilities in good faith without exfiltrating clinical data, degrading system availability, or violating user privacy.

---

## 4. Architectural Security Controls

### A. Authentication & Session Management
- **Stateless Asymmetric/HMAC Tokens:** Signed JWT access tokens with strict lifetime limits (15 minutes).
- **Token Rotation & Replay Protection:** Dedicated rotating refresh tokens (7 days). On each refresh, the previous refresh token `jti` is permanently invalidated and blacklisted.
- **Instant Logout & Revocation:** Blacklist registry (`store.revoked_tokens`) immediately blocks revoked session JTIs.
- **Password Hardening:** Minimum 8 characters, uppercase, numeric digits, and salted `bcrypt` hashing.

### B. Authorization & Multi-Tenant Isolation
- **Role-Based Access Control (RBAC):** Five discrete roles (`CITIZEN`, `HEALTH_WORKER`, `CLINICIAN`, `PUBLIC_HEALTH_ADMIN`, `SYSTEM_ADMIN`).
- **Care Context & Need-to-Know:** Clinicians can only access patient charts if the patient is on their assigned panel, in their triage escalation queue, or has granted an active, time-bound ABDM consent directive.
- **IDOR Protection:** Citizens are cryptographically scoped to their own records (`citizen.user_id == actor.sub`); cross-patient queries return HTTP 403 Forbidden.
- **Tenant Isolation:** Mandatory `tenant_id` foreign keys and boundary checks prevent data leakage across distinct jurisdictions (e.g. Mandya vs. Mysuru).

### C. Secret Management & Zero Secrets in Code
- **Rule:** **API keys, database passwords, and cryptographic seeds are strictly forbidden from source code or git commits.**
- **Environment Driven:** Managed exclusively via Pydantic `BaseSettings` (`packages/config/settings.py`) backed by secure secret vaults (e.g. AWS Secrets Manager / HashiCorp Vault).
- **Startup Audit:** Automated startup validation checks fail immediately if insecure default secrets are detected in production environments.

### D. Secure HTTP Headers & Defense-in-Depth
- **Content Security Policy (CSP):** `default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'`
- **Clickjacking Defense:** `X-Frame-Options: DENY`
- **MIME Defense:** `X-Content-Type-Options: nosniff`
- **XSS Protection:** `X-XSS-Protection: 1; mode=block`
- **HSTS Enforcement:** `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- **Cache-Control:** `no-store, no-cache, must-revalidate` on all sensitive authentication and clinical routes.

### E. API Abuse & Sliding-Window Rate Limiting
- **Adaptive Rate Limiting:** Enforced via `RateLimiterMiddleware` (`packages/security/rate_limiter.py`):
  - Authentication endpoints: **20 requests/minute**
  - AI conversational agent endpoints: **40 requests/minute**
  - Document ingestion OCR endpoints: **15 requests/minute**
  - General API routes: **120 requests/minute**
- Returns standard HTTP 429 Too Many Requests with `Retry-After` headers.

### F. Input Validation, XSS & SSRF Guards
- **XSS Sanitization:** User-submitted text is stripped of dangerous script tags, event handlers, and escaped before rendering.
- **SSRF Defense:** `SSRFGuard` validates outbound webhook and FHIR URLs against private IPv4/IPv6 CIDRs (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`), preventing cloud metadata compromise.
- **SQL / GraphQL Injection:** `AntiArbitraryQueryGuard` blocks raw SQL strings, stacked queries, and unauthorized GraphQL queries.

### G. Secure File Uploads & Malware Scanning
- **MIME & Magic Byte Verification:** Verifies file content magic bytes matching declared extensions (`%PDF-`, `\x89PNG`, `\xFF\xD8\xFF`).
- **Path Traversal Defense:** Sanitizes filenames using base-name isolation, strips directory separators (`/`, `\`, `..`), and rejects null bytes (`%00`).
- **Signature Scanning:** Scans for executable headers (`MZ`, `\x7fELF`, shell shebangs `#!`), EICAR antivirus test signatures, and enforces a 15 MB file size limit.

### H. Encryption in Transit and at Rest
- **In Transit:** TLS 1.3 enforced across all external and internal microservice channels.
- **At Rest:** Database storage and MinIO object vault encrypted with AES-256. Sensitive field attributes (ABHA IDs, mobile numbers) protected with authenticated AES-256-GCM (`packages/security/encryption.py`).

### I. AI Agent Safety, Prompt Injection & Data Privacy
- **Scrubbed Logging:** Healthcare data and raw biomarkers (BP, glucose, creatinine) are strictly scrubbed from ordinary stdout logs via `HealthcareLogSanitizer`.
- **Prompt Injection Defense:** Automated detection of jailbreaks, DAN mode overrides, and system prompt tampering in `ClinicalSafetyEngine`.
- **Tool Calling Whitelist:** AI agents execute through strictly parameterized, typed tools; arbitrary code or direct database execution is prohibited.
- **Non-Diagnostic Boundaries:** Mandatory `NON_DIAGNOSTIC_NOTICE` on all AI-generated envelopes; autonomous prescription of medication is blocked.

### J. Forensic Audit Logging
- Every authentication, permission change, consent directive, record access, and export event is immutably recorded in `AuditLogger` (`packages/observability/audit.py`), tagged with actor ID, role, tenant ID, correlation ID, and client IP.

---

*Policy Maintained by SevaHealth AI Security & Privacy Governance Board.*  
*Last Reviewed: October 2026*
