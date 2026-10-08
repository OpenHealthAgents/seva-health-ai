# SevaHealth AI - Code & Architecture Reuse Matrix

This document provides a comprehensive inventory of all architectural references, modules, frameworks, and patterns evaluated and reused in **SevaHealth AI** for the *Seva First Innovation Challenge*.

In strict compliance with open-source licensing principles, **no copyright or license notices are removed**, and all original authors receive clear attribution.

---

## 1. Summary of Evaluated Repositories

| Repository | Upstream URL | Declared License | Reused Status | Primary Reused Layer |
|---|---|---|---|---|
| **bezs-iam** | https://github.com/Yazhnimalan/bezs-iam | MIT License (2026) | Reused | Multi-tenant RBAC, Auth contracts, Audit trail patterns |
| **bezs-filenest** | https://github.com/Yazhnimalan/bezs-filenest | MIT License (2026) | Reused | S3/MinIO file vault, Lab report storage, Presigned URLs |
| **bezs-pipeline** | https://github.com/alphaesAI/bezs-pipeline | MIT License (2026) | Reused | ETL ingestion schemas, Clinical data transformation |
| **refactoragent** | https://github.com/Kipla1412/refactoragent | Open Source / MIT Compatible | Reused | Clinical AI agent safety rails, LLM client abstraction, Assessment prompts |
| **bezs-hms** | https://github.com/Yazhnimalan/bezs-hms | MIT License (2026) | Reused | Clinical encounter models, Clinician review workflows, shadcn UI components |
| **DrGodly-Mobile-Aplication** | https://github.com/Saythu000/DrGodly-Mobile-Aplication | Open Reference | Reused | Mobile pre-visit intake UX, Health Connect/BLE wearable bridge architecture |
| **bezs-emr-core / EHRbase** | https://github.com/Yazhnimalan/bezs-emr-core / ehrbase | Apache License 2.0 (2024) | Reused | Clinical archetypes, OpenEHR / FHIR R4 domain mapping concepts |
| **bezs-emr-gql** | https://github.com/Yazhnimalan/bezs-emr-gql | MIT License (2026) | Reused | FHIR R4 Pydantic schemas, LOINC / SNOMED terminology codes |
| **bezs-emr-mcp** | https://github.com/Yazhnimalan/bezs-emr-mcp | MIT License (2026) | Reused | Model Context Protocol (MCP) tool schema for AI agent EMR access |
| **bezs-observability** | https://github.com/Yazhnimalan/bezs-observability | MIT License (2026) | Reused | OpenTelemetry tracing middleware, Python SDK buffer & flusher, Audit logging |
| **open-wearables** | https://github.com/the-momentum/open-wearables | MIT License (2025) | Reused | Normalized wearable timeseries biometrics (HR, HRV, Sleep, Steps) |

---

## 2. Detailed Component Reuse & Modification Inventory

### 2.1. `bezs-iam`
* **Repository**: https://github.com/Yazhnimalan/bezs-iam
* **License**: MIT License (Copyright (c) 2026 Yazhnimalan)
* **Reused Component**: Multi-tenant authorization model, JWT token lifecycle, role-based access control (RBAC), and immutable audit log schemas.
* **Files / Modules Reused**:
  - `prisma/schema/schema.prisma` (User, Role, Session, AuditLog, Tenant models)
  - `src/lib/permissions.ts` (Permission matrix for clinical vs citizen vs public health roles)
* **Modifications Made**:
  - Transposed Prisma schema concepts into FastAPI SQLAlchemy 2.0 and Pydantic models.
  - Implemented 4 distinct roles: `CITIZEN`, `HEALTH_WORKER`, `CLINICIAN`, and `POPULATION_ADMIN`.
  - Added ABHA (Ayushman Bharat Health Account) linking capabilities for citizen identity.
* **Reason for Reuse**: Avoided reinvention of enterprise healthcare RBAC and multi-tenancy isolation.
* **Attribution Requirement**: MIT License attribution retained.

---

### 2.2. `bezs-filenest`
* **Repository**: https://github.com/Yazhnimalan/bezs-filenest
* **License**: MIT License (Copyright (c) 2026 Yazhnimalan)
* **Reused Component**: Object storage service abstractions (S3 / MinIO compatible) with MIME validation, checksum verification, and secure pre-signed URLs.
* **Files / Modules Reused**:
  - `backend/app/storage/` (Storage adapter interface)
  - `backend/app/services/` (Presigned URL generation and file metadata extraction)
* **Modifications Made**:
  - Integrated into SevaHealth for uploading citizen lab reports (PDF/images of lipid panels, HbA1c tests, ECGs) and automated metadata indexing.
* **Reason for Reuse**: Production-ready, secure file upload and storage layer with encrypted bucket isolation.
* **Attribution Requirement**: MIT License attribution retained.

---

### 2.3. `bezs-pipeline`
* **Repository**: https://github.com/alphaesAI/bezs-pipeline
* **License**: MIT License (Copyright (c) 2026 alphaesAI)
* **Reused Component**: Structured data loading, clinical data cleaning, and validation pipelines.
* **Files / Modules Reused**:
  - `src/schemas/` and `src/components/` data validator abstractions.
* **Modifications Made**:
  - Adapted to validate community-based screening datasets (CBAC / IDRS survey responses, vitals batches from health camps).
* **Reason for Reuse**: Ensures high-integrity ingestion of messy field data from remote primary health centers.
* **Attribution Requirement**: MIT License attribution retained.

---

### 2.4. `refactoragent`
* **Repository**: https://github.com/Kipla1412/refactoragent
* **License**: Open Source / MIT Compatible
* **Reused Component**: Clinical AI agent architecture, LLM client provider abstractions, structured JSON response parsing, safety validation barriers, and SOAP note generation.
* **Files / Modules Reused**:
  - `client/llm_client.py` (Multi-provider model client abstraction)
  - `safety/approval.py` (Safety approval engine and boundary enforcer)
  - `customagents/previsitagent/intakeagent.py` & `intakeprompt.py`
  - `customagents/reportagent/assesment.py`
* **Modifications Made**:
  - Re-architected prompts specifically for **NCD early-warning and preventive lifestyle medicine** (ICMR guidelines, WHO SEAR criteria).
  - Enforced strict non-diagnostic clinical boundaries: the system outputs preventive risk stratification, personalized lifestyle interventions, and clinical review flags, but never prescribes medications or autonomous diagnoses.
  - Added fallback deterministic mock provider so the platform runs flawlessly offline or during challenge evaluation without mandatory external API keys.
* **Reason for Reuse**: Robust clinical reasoning agent patterns and safety boundaries.
* **Attribution Requirement**: Retained notice and attribution to `refactoragent`.

---

### 2.5. `bezs-hms`
* **Repository**: https://github.com/Yazhnimalan/bezs-hms
* **License**: MIT License (Copyright (c) 2026 Yazhnimalan)
* **Reused Component**: Clinical UI components (Tailwind CSS, shadcn/ui), patient summary cards, clinician review review-queue workflows, and consultation lifecycle states.
* **Files / Modules Reused**:
  - `prisma/schema/schema.prisma` (Intake and Consultation lifecycle models)
  - UI patterns from Next.js app components and layout structure.
* **Modifications Made**:
  - Extended consultation review to include NCD risk trajectories, SHAP-like risk factor waterfalls, and 30-day intervention sign-off.
* **Reason for Reuse**: Modern, accessible clinical UI patterns tailored for Indian healthcare delivery.
* **Attribution Requirement**: MIT License attribution retained.

---

### 2.6. `DrGodly-Mobile-Aplication`
* **Repository**: https://github.com/Saythu000/DrGodly-Mobile-Aplication
* **License**: Open Reference Architecture
* **Reused Component**: Mobile pre-visit intake conversation flow, FHIR API client patterns, and Bluetooth LE / Android Health Connect bridge concepts.
* **Files / Modules Reused**:
  - `docs/INTAKE_FEATURE_DOCUMENTATION.md` (Intake conversation sequence)
  - `docs/open_wearables_device_compatibility.md` (Wearable sensor matrix)
  - `lib/data/service/fhir_api_client.dart` (REST/FHIR network client conventions)
* **Modifications Made**:
  - Applied mobile-first screening principles for community health workers (ASHAs/ANMs) and citizens conducting at-home screening.
* **Reason for Reuse**: Pragmatic mobile-first healthcare delivery patterns.
* **Attribution Requirement**: Reference and architecture credit to Saythu000.

---

### 2.7. `bezs-emr-core` / `ehrbase`
* **Repository**: https://github.com/Yazhnimalan/bezs-emr-core / ehrbase
* **License**: Apache License 2.0 (Copyright (c) 2019-2024 openEHR Foundation & EHRbase contributors)
* **Reused Component**: OpenEHR archetype concepts, clinical observation definitions, and international EHR interoperability models.
* **Files / Modules Reused**:
  - Conceptual mapping of vital signs, blood glucose monitoring, blood pressure summaries, and chronic disease evaluation.
* **Modifications Made**:
  - Mapped archetype concepts directly into lightweight HL7 FHIR R4 JSON resources for seamless ABDM (Ayushman Bharat Digital Mission) compliance.
* **Reason for Reuse**: Guarantees international medical informatics rigor and ABDM compatibility.
* **Attribution Requirement**: Apache License 2.0 attribution retained.

---

### 2.8. `bezs-emr-gql`
* **Repository**: https://github.com/Yazhnimalan/bezs-emr-gql
* **License**: MIT License (Copyright (c) 2026 Yazhnimalan)
* **Reused Component**: FHIR R4 Pydantic schema models, LOINC and SNOMED CT terminology mappings for clinical observations and conditions.
* **Files / Modules Reused**:
  - `app/schemas/observation/`
  - `app/schemas/patient/`
  - `app/schemas/terminology.py`
  - `app/schemas/enums.py`
* **Modifications Made**:
  - Enriched with NCD-specific LOINC codes:
    - 4548-4 (Hemoglobin A1c)
    - 1558-6 (Fasting Glucose)
    - 8480-6 (Systolic BP)
    - 8462-4 (Diastolic BP)
    - 2093-3 (Total Cholesterol)
    - 2085-9 (HDL Cholesterol)
    - 2571-8 (Triglycerides)
    - 8280-0 (Waist Circumference)
    - 33914-3 (eGFR)
* **Reason for Reuse**: Complete, standards-compliant FHIR R4 schema typing in Python/Pydantic.
* **Attribution Requirement**: MIT License attribution retained.

---

### 2.9. `bezs-emr-mcp`
* **Repository**: https://github.com/Yazhnimalan/bezs-emr-mcp
* **License**: MIT License (Copyright (c) 2026 Yazhnimalan)
* **Reused Component**: Model Context Protocol (MCP) server design for decoupling AI agents from clinical databases.
* **Files / Modules Reused**:
  - MCP tool interface conventions for querying patient records, vitals histories, and previous screenings.
* **Modifications Made**:
  - Standardized tool signatures (`get_citizen_vitals`, `get_screening_history`, `record_risk_assessment`).
* **Reason for Reuse**: Allows LLM agents to call clinical tools through a standardized, auditable protocol.
* **Attribution Requirement**: MIT License attribution retained.

---

### 2.10. `bezs-observability`
* **Repository**: https://github.com/Yazhnimalan/bezs-observability
* **License**: MIT License (Copyright (c) 2026 Yazhnimalan)
* **Reused Component**: OpenTelemetry tracing middleware, event buffer flusher, and structured health event telemetry.
* **Files / Modules Reused**:
  - `sdk/python/src/watcher_sdk/` (Event buffer, client, flusher, FastAPI middleware pattern)
* **Modifications Made**:
  - Added dedicated clinical audit events (`RISK_ASSESSED`, `INTERVENTION_GENERATED`, `CLINICIAN_ESCALATED`, `CARE_PLAN_REVIEWED`).
* **Reason for Reuse**: Rigorous observability and compliance auditing for sensitive healthcare interactions.
* **Attribution Requirement**: MIT License attribution retained.

---

### 2.11. `open-wearables`
* **Repository**: https://github.com/the-momentum/open-wearables
* **License**: MIT License (Copyright (c) 2025 Momentum)
* **Reused Component**: Standardized wearable time-series schema, normalization algorithms for resting heart rate, HRV, sleep architecture, and daily activity.
* **Files / Modules Reused**:
  - `backend/app/schemas/` (Timeseries biometric schemas)
  - `backend/app/algorithms/` (Scoring primitives, sleep scoring concepts)
* **Modifications Made**:
  - Mapped wearable biometrics into physiological early warning indicators for metabolic and cardiovascular deterioration.
* **Reason for Reuse**: Eliminates vendor lock-in and enables universal wearable data ingestion.
* **Attribution Requirement**: MIT License attribution retained.

---

## 3. Compliance and Verification Statement
All reused code snippets and architectural patterns have been examined for intellectual property provenance. SevaHealth AI enforces:
1. Complete preservation of upstream MIT and Apache 2.0 notices.
2. Clean separation of proprietary challenge logic (NCD risk scoring, explainability engine, intervention planner) and open-source infrastructure.
3. No inclusion of proprietary, restricted, or unlicensed code.
