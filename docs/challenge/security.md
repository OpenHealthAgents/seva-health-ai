# SevaHealth AI — Security, Privacy & Data Protection Architecture

> **Regulatory Compliance**: Digital Information Security in Healthcare Act (DISHA), Digital Personal Data Protection (DPDP) Act 2023, ABDM Security Guidelines, OWASP Top 10

---

## 1. Zero-Leakage PHI Logging Architecture

A severe vulnerability in typical health platforms is the accidental leakage of Protected Health Information (PHI) into unencrypted log aggregators (e.g. stdout, Elasticsearch, Datadog).

SevaHealth AI enforces strict **in-flight log sanitization** via `packages/observability/sanitizer.py`:
- All hemodynamic vitals (`systolic_bp`, `diastolic_bp`, `glucose`, `hba1c`, `spo2`) are automatically scrubbed or replaced with `[REDACTED_CLINICAL_VALUE]`.
- All patient direct identifiers (`abha_id`, `aadhaar_id`, `first_name`, `phone_number`) are masked.
- Application logs contain **only opaque correlation IDs** (`X-Correlation-ID`) and status codes.

---

## 2. Authentication, RBAC & Multi-Tenant Isolation

1. **Password Security**: Passwords hashed using bcrypt (12 rounds) with salted key derivation.
2. **Stateless JWT Security**: Signed using HMAC-SHA256 with 60-minute access token lifespan and encrypted refresh tokens.
3. **Role-Based Least Privilege (RBAC)**:
   - `CITIZEN`: Access restricted exclusively to their own longitudinal profile.
   - `HEALTH_WORKER`: Scoped strictly to their designated geographic ward or health camp.
   - `CLINICIAN`: Authorized to review triage queues and approve care plans within their assigned hospital or PHC.
   - `PUBLIC_HEALTH_OFFICER`: Restricted to de-identified aggregate cohort queries; blocked from viewing individual identifiable citizen records.
4. **Tenant Isolation**: Every database query explicitly filters on `tenant_id` and jurisdiction, preventing cross-organization or cross-district data leakage.

---

## 3. Threat Model & Mitigations Matrix

| Attack Vector | Threat Description | SevaHealth Mitigation |
|:---|:---|:---|
| **Insecure Direct Object Reference (IDOR)** | Malicious user attempts to read another citizen's records by guessing UUIDs | Tenant-scoped RBAC validator strictly asserts token subject against requested resource |
| **SQL & Command Injection** | Attacker injects SQL payloads into screening inputs | SQLAlchemy parameterized queries & Pydantic strict typing |
| **Cross-Site Scripting (XSS)** | Malicious script injected into clinical notes | Content-Security-Policy (CSP) headers & HTML sanitization |
| **Server-Side Request Forgery (SSRF)**| Exploiting document OCR or webhook URLs to probe internal networks | Hardened internal network isolation & URL allowlist |
| **Malicious Document Upload** | Uploading malware masked as lab PDFs | MIME magic-byte verification, file size quotas (25MB), and isolated MinIO S3 storage |
| **API Denial of Service (DoS)** | Automated brute-force credential stuffing | NGINX rate-limiting zones (10 req/s on `/auth`, 40 req/s on `/api`) |
| **Cross-Patient Data Leakage in AI** | LLM context retention causing data spillover | Ephemeral conversation contexts with automated context clearance per request |
