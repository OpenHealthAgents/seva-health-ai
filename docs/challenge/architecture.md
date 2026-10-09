# SevaHealth AI — Strategic Architecture Specification

> **Design Paradigm**: Domain-Driven Layered Microservice Topology with Bounded Generative AI  
> **Core Principle**: *"Deterministic models calculate risk. LLMs explain and orchestrate. Human clinicians make decisions."*

---

## 1. High-Level Strategic Architecture

SevaHealth AI acts as the unified intelligence layer above hardened, reusable healthcare infrastructure:

```
                            SEVAHEALTH AI PLATFORM
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
            ▼                         ▼                         ▼
   CITIZEN MOBILE APP        HEALTH WORKER PORTAL        CLINICIAN COPILOT
   - Vital 4 Questions       - Quick Intake (<3m)        - Triage SOAP Notes
   - Trajectory View         - Offline Sync Queue        - Care Plan Approval
   - Vernacular Audio        - Defaulter Rosters         - Clinical Escalations
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                            SEVAHEALTH CORE GATEWAY
                          (FastAPI / NGINX / RBAC)
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
   NCD RISK CALCULATION       BOUNDED MULTI-AGENT       LIFESTYLE INTERVENTION
          ENGINE                DECISION ENGINE                 ENGINE
   - ICMR-INDIAB IDRS         - Trajectory Explainer    - 30-Day Multi-Pillar Plans
   - WHO Asian Indian CVD     - Vernacular Coach        - Micro-Habit Generation
   - KDIGO Renal Matrix       - Clinical Summarizer     - Daily Adherence Tracking
   - Deterministic Math       - Safety Envelope         - Follow-up Surveillance
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                        PERSONAL HEALTH TRAJECTORY
                       (Longitudinal Temporal Store)
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
   WEARABLE TELEMETRY        LONGITUDINAL CLINICAL     UNSTRUCTURED MEDICAL
        PIPELINE                  REPOSITORY                 DOCUMENTS
   (Open Wearables Layer)      (openEHR / EHRbase)       (FileNest Vault / OCR)
   - Apple, Garmin, Fitbit    - Blood Pressure Archetype- Presigned S3 Storage
   - Rolling 7-Day Baseline   - Lab Test Archetype      - Medical Report Parser
   - Steps, HRV, Sleep Debt   - PostgreSQL Dual-Write   - Anti-Malware Inspection
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                      POPULATION INTELLIGENCE LAYER
               (District Hotspots & Geospatial Epidemiology)
```

---

## 2. The Critical Architectural Separation: Deterministic vs Generative

A foundational flaw in early healthcare GenAI applications was prompting large language models to diagnose conditions or invent numerical risk probabilities.

SevaHealth AI enforces a strict architectural boundary:

```
                          RAW INCOMING OBSERVATIONS
               (BP: 142/92, Fasting Glucose: 114 mg/dL, Steps: 3,400)
                                      │
                                      ▼
                        VALIDATION & ADAPTATION LAYER
                  (MIME checks, LOINC mapping, Range sanity)
                                      │
                                      ▼
                         CANONICAL DATA ENTITIES
                     (VitalSign, LabResult, WearableObs)
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
   CLINICAL RULE MATRIX                             CALIBRATED ML PIPELINES
   - ICMR IDRS Scoring                              - Isotonic Calibrated Models
   - WHO Framingham CVD Risk                        - Brier Score Verified
   - KDIGO Staging Matrix                           - Scikit-learn Pipeline
            │                                                   │
            └─────────────────────────┬─────────────────────────┘
                                      │
                                      ▼
                        DETERMINISTIC RISK VECTOR
                 [ Metabolic: 0.81, CVD: 0.64, Renal: 0.38 ]
                                      │
                                      ▼
                      TEMPORAL RISK TRAJECTORY MODEL
                   [ Velocity: +35%/quarter | Trend: WORSENING ]
                                      │
                                      ▼
                     BOUNDED EXPLAINABLE AI AGENTS
                   - Translates mathematical vector to plain Kannada/Hindi/English
                   - Generates transparent attribution waterfall
                   - Proposes multi-pillar lifestyle intervention
                   - Zero numerical hallucination allowed
                                      │
                                      ▼
                        HUMAN CLINICIAN VERIFICATION
                   - Doctor reviews and stamps proposed plan
                   - Prevents automated unsupervised medical advice
```

---

## 3. Technology Integration Architecture

| Integrated Foundation | Architectural Role in SevaHealth AI | Integration Layer |
|:---|:---|:---|
| **Open Wearables** | Ingests, normalizes, and computes rolling baselines from consumer wearables | `services/wearable/adapter.py` |
| **EHRbase** | openEHR clinical archetype repository for universal health record portability | `packages/clinical_models/openehr_builder.py` |
| **bezs-iam** | Role-Based Access Control, JWT authentication, and multi-tenant health jurisdictions | `packages/auth/jwt.py`, `services/identity/` |
| **bezs-filenest** | Secure S3 medical vault, presigned upload URLs, and anti-tamper checksums | `services/documents/`, MinIO S3 |
| **bezs-observability** | Request correlation tracking (`X-Correlation-ID`), metrics, and PHI log sanitization | `packages/observability/` |
| **bezs-emr-gql** | Federated GraphQL connectivity to legacy hospital EMR systems | `services/clinical/emr_federation.py` |
| **bezs-hms** | Hospital Management System outpatient appointments and triage referrals | `services/clinical/hms_client.py` |
| **FastAPI Core** | High-performance async ASGI gateway routing clinical domains | `services/api/main.py` |
| **PostgreSQL 16** | Primary relational clinical store with transactional schema migrations | `infrastructure/postgres/` |
| **Redis 7** | Non-blocking priority queue broker for OCR, wearable backfills, and AI agents | `packages/queue/`, `services/jobs/` |
| **NGINX Reverse Proxy** | Unified gateway, TLS 1.3 termination, OWASP security headers, and rate limiting | `infrastructure/nginx/nginx.conf` |
