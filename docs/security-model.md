# SevaHealth AI: Security, Privacy & Compliance Architecture

**Document Version:** 1.1.0  
**Target:** SevaHealth AI Platform  
**Compliance Foundations:** Digital Information Security in Healthcare Act (DISHA - India), Ayushman Bharat Digital Mission (ABDM) Data Privacy Policies, ISO/IEC 27001, HIPAA Security & Privacy Rules  
**Implementation Source Reference:** Adapted from `bezs-iam` and `bezs-observability`  

---

## 1. Security Architecture Principles

Healthcare data is among the most sensitive categories of personal information. SevaHealth AI enforces **Security-by-Design** and **Zero-Trust Architecture** across all components.

The platform is governed by eight foundational security tenets:
1. **Tenant Isolation:** Complete logical and cryptographic isolation between healthcare jurisdictions and organizations.
2. **Strict RBAC & Least Privilege:** Role, care context, and jurisdiction-enforced access boundaries on every single API endpoint.
3. **Immutable Audit Trails:** Forensic logging of every access, modification, export, or AI generation event.
4. **Encryption by Default:** TLS 1.3 in transit and AES-256 at rest.
5. **No Secrets in Code:** 100% environment-variable driven configuration with validation on server startup.
6. **Explicit Patient Consent:** Granular, time-bound consent directives modeled after ABDM guidelines.
7. **Safe AI Boundaries:** Input sanitization, strict JSON schema validation, and guardrails against prompt injection.
8. **Defense in Depth:** Rate limiting, IP filtering, and continuous input/output schema validation.

---

## 2. Multi-Tenant Architecture & Data Isolation

Public health systems require clear administrative hierarchy without data leakage:

```
[State Health Ministry: karnataka_state_health]
    ├── [District Health Office: mysuru_district_health]
    └── [District Health Office: mandya_district_health]
```

* **Tenant Identifier:** Every citizen, screening record, observation, care plan, and triage case contains a mandatory `tenant_id` foreign key.
* **Database & Memory Filtering:** All data queries automatically enforce tenant boundaries via `HealthcareAuthorizationEngine`.
* **Cross-Tenant Prevention:** Attempts to access records outside a user's authorized tenant hierarchy trigger security alerts (`403 FORBIDDEN`) and an immediate audit event. (Verified in `test_cross_tenant_isolation`).

---

## 3. Role-Based Access Control (RBAC) & Least-Privilege Matrix

| Resource / Endpoint | `CITIZEN` | `HEALTH_WORKER` | `CLINICIAN` | `PUBLIC_HEALTH_ADMIN` | `SYSTEM_ADMIN` |
|---|---|---|---|---|---|
| **View Own Health Record** | ✅ Allow | ❌ Deny | ❌ Deny | ❌ Deny | ✅ Allow |
| **View Other Citizens** | ❌ Deny (403) | ❌ Deny (403) | ❌ Deny (403) | ❌ Deny (403) | ✅ Allow |
| **Assigned Care Context Patient** | ❌ Deny | ❌ Deny | ✅ Allow | ❌ Deny | ✅ Allow |
| **Pending Triage Patient** | ❌ Deny | ❌ Deny | ✅ Allow | ❌ Deny | ✅ Allow |
| **Patient with Active Consent** | ❌ Deny | ✅ Allow | ✅ Allow | ❌ Deny | ✅ Allow |
| **Assigned Ward / Jurisdiction** | ❌ Deny | ✅ Allow | ❌ Deny | ❌ Deny | ✅ Allow |
| **Citizen Registry Enumeration** | 🔒 Own Record Only | 🔒 Jurisdiction Only | 🔒 Care Panel Only | ❌ Deny (403) | ✅ Tenant Scope |
| **Submit Screening Survey** | ✅ Allow | ✅ Allow (Field Camp) | ❌ Deny | ❌ Deny | ✅ Allow |
| **Clinician Triage Queue** | ❌ Deny | ❌ Deny | ✅ Allow | ❌ Deny | ✅ Allow |
| **Approve / Sign Off Care Plan** | ❌ Deny | ❌ Deny | ✅ Allow | ❌ Deny | ✅ Allow |
| **Aggregated Epidemiological Metrics**| ❌ Deny | ❌ Deny | ✅ Allow | ✅ Allow | ✅ Allow |
| **Intervention Outcome Deltas** | ❌ Deny | ❌ Deny | ✅ Allow | ✅ Allow | ✅ Allow |
| **Grant / Revoke Consent** | ✅ Allow (Own) | ❌ Deny | ❌ Deny | ❌ Deny | ✅ Allow |
| **User & Tenant Management** | ❌ Deny | ❌ Deny | ❌ Deny | ❌ Deny | ✅ Allow |
| **Forensic Audit Trails** | ❌ Deny | ❌ Deny | ❌ Deny | ❌ Deny | ✅ Allow |

---

## 4. Healthcare Authorization Engine (`HealthcareAuthorizationEngine`)

Located in `packages/auth/access_control.py` and enforced on all citizen and clinical endpoints:

### Rule 1: Citizen Isolation
A citizen can strictly access only their own medical records (`citizen.user_id == actor.sub or citizen.id == actor.sub`). Any attempt by Citizen A to view Citizen B's medical data results in immediate `403 FORBIDDEN` (`"Access denied. Citizens can only access their own medical records"`).

### Rule 2: Clinician Need-to-Know & Care Context
A clinician can access patient health records **only** under three verified clinical contexts:
1. **Assigned Care Panel:** Patient is in clinician's `assigned_patients` panel.
2. **Clinical Triage Escalation:** Patient is in the pending `ClinicalTriageCase` escalation queue requiring physician sign-off.
3. **Explicit Patient Consent:** Citizen has granted an active, non-expired ABDM consent directive (`ConsentDirective`) to this clinician.
Any attempt to access an unassigned citizen without consent triggers `403 FORBIDDEN`.

### Rule 3: Health Worker Jurisdiction Scoping
A health worker (ASHA / ANM) is restricted to citizens residing in their assigned village, ward, or district program boundary (`assigned_jurisdiction`), or where active field consent was granted. Attempts to access out-of-jurisdiction citizens trigger `403 FORBIDDEN`.

### Rule 4: Public Health Administrator Aggregate Isolation
Public Health Administrators are strictly forbidden from viewing identifiable, individual citizen health records or enumerating the citizen registry (`403 FORBIDDEN`). They are granted access exclusively to de-identified, aggregated population analytics endpoints (`/api/v1/population/metrics` and `/api/v1/population/outcome-delta`).

---

## 5. Token Lifecycle, Session Management & Token Revocation

Adapted from patterns in `bezs-iam`:

* **Access Tokens:** Signed JWT with `sub`, `tenant_id`, `role`, `scopes`, and unique `jti` (UUID). Lifetime: 15 minutes.
* **Rotating Refresh Tokens:** Dedicated token type (`type: "refresh"`) with 7-day lifetime. On refresh (`POST /api/v1/auth/refresh`), the old refresh token `jti` is permanently revoked and a new key pair is issued to protect against token replay attacks.
* **Instant Logout & Revocation:** When `/api/v1/auth/logout` is called, the token's `jti` is added to `store.revoked_tokens`. Subsequent requests immediately fail with `401 UNAUTHORIZED` (`"Token has been revoked / logged out"`).
* **Session Tracking:** Every login creates a `SessionRecord` capturing user ID, client IP, user agent, expiration, and revocation status (`GET /api/v1/auth/sessions`).

---

## 6. Password Security & Account Recovery

* **Password Complexity Policy:**
  - Minimum 8 characters.
  - At least one uppercase letter.
  - At least one numeric digit.
  - Validated on registration and password reset via `validate_password_strength()`.
* **Password Hashing:** Native `bcrypt` salted hash with fallback to SHA-256.
* **Account Recovery Workflow:**
  1. `POST /api/v1/auth/recover/request`: Generates a high-entropy 32-character hexadecimal recovery token valid for 15 minutes.
  2. `POST /api/v1/auth/recover/reset`: Validates recovery token, enforces password strength on the new password, updates credentials, invalidates the token, and revokes all active sessions for the user.

---

## 7. Patient Consent Directives (ABDM / DISHA Alignment)

* **Grant Consent (`POST /api/v1/auth/consent/grant`):** Citizens specify grantee ID, grantee role (`CLINICIAN`, `HEALTH_WORKER`), purpose (`CARE_DELIVERY`, `RESEARCH`), and expiration duration.
* **Revoke Consent (`POST /api/v1/auth/consent/revoke`):** Citizens can revoke consent directives at any time with immediate effect.
* **Consent Verification:** Evaluated in real-time during every clinical record access.

---

## 8. Immutable Audit Logging (adapted from `bezs-observability`)

Every security-sensitive event is captured with tenant ID, actor ID, role, timestamp, action type, resource type, and IP address:

```
AuditAction Taxonomy:
- USER_REGISTERED
- LOGIN_SUCCESS
- LOGOUT
- PASSWORD_RESET
- CONSENT_GRANTED
- CONSENT_REVOKED
- ACCESS_DENIED
- SCREENING_SUBMITTED
- RISK_ASSESSED
- CARE_PLAN_GENERATED
- TASK_COMPLETED
- WEARABLE_SYNCED
- CLINICIAN_REVIEWED
- DATA_EXPORTED
```

---

## 9. Test Verification Matrix

All security controls and authorization boundaries are verified in `tests/test_iam_authorization.py`:

| Test Name | Objective | Result |
|---|---|---|
| `test_citizen_self_access_allowed` | Verify Citizen A accesses Citizen A | ✅ PASSED |
| `test_citizen_cross_access_forbidden` | Verify Citizen A blocked from Citizen B (403) | ✅ PASSED |
| `test_citizen_listing_scoped_to_self` | Verify Citizen registry list scoped only to self | ✅ PASSED |
| `test_clinician_accesses_assigned_patient` | Verify Clinician accesses panel patient | ✅ PASSED |
| `test_clinician_accesses_triage_patient` | Verify Clinician accesses triage queue patient | ✅ PASSED |
| `test_clinician_blocked_from_unassigned_patient_without_consent` | Verify Clinician blocked from unassigned patient without consent (403) | ✅ PASSED |
| `test_consent_grant_and_revoke_lifecycle` | Verify ABDM consent grant authorizes doctor, and revocation blocks doctor | ✅ PASSED |
| `test_health_worker_jurisdiction_scoping` | Verify ASHA worker allowed in Ward 12, blocked in Highway Corridor Ward | ✅ PASSED |
| `test_public_health_admin_blocked_from_identifiable_records` | Verify Admin blocked from raw patient records and list (403) | ✅ PASSED |
| `test_public_health_admin_allowed_aggregate_population_endpoints` | Verify Admin allowed access to regional metrics and outcome deltas | ✅ PASSED |
| `test_cross_tenant_isolation` | Verify Mandya worker blocked from Mysuru citizen (403) | ✅ PASSED |
| `test_logout_revokes_token` | Verify logout invalidates JTI and blocks subsequent calls (401) | ✅ PASSED |
| `test_refresh_token_lifecycle` | Verify refresh token rotation and replay prevention (401) | ✅ PASSED |
| `test_registration_password_strength_and_uniqueness` | Verify password complexity and duplicate check | ✅ PASSED |
| `test_account_recovery_flow` | Verify token issuance, reset, session revocation, and re-login | ✅ PASSED |
