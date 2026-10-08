# SevaHealth AI: Phased Implementation Plan

**Document Version:** 1.0.0  
**Target:** SevaHealth AI Platform (Seva First Innovation Challenge)  
**Execution Standard:** Strictly incremental. Each phase includes coding, testing, linting/type checks, integration verification, and documentation updates before moving to the next.

---

## 1. Phased Implementation Roadmap

```
PHASE 1: Foundation, Data Layer & IAM
  ├── Core FastAPI application scaffold with Pydantic v2 settings & CORS
  ├── Database schema (SQLAlchemy 2.0 models + SQLite/Postgres dual-mode)
  ├── RBAC Security & JWT Bearer Token infrastructure (adapted from bezs-iam)
  └── Unit tests for auth, tenant isolation, and audit logging

PHASE 2: Screening & Clinical Observations Engine
  ├── LOINC-coded Observation models and FHIR R4 mapping (adapted from bezs-emr-gql)
  ├── Community-Based Assessment Checklist (CBAC) & Indian Diabetes Risk Score (IDRS)
  ├── Screening validation pipelines (adapted from bezs-pipeline)
  └── Unit & integration tests for screening ingestion & validation

PHASE 3: Deterministic Guidelines & AI Risk Engine
  ├── Mathematical guidelines engine: ICMR IDRS, AHA/ACC HTN, WHO-SEAR 10-yr CVD, Asian Indian BMI/Waist
  ├── Multi-factor risk stratifier (Diabetes, HTN, CVD, Metabolic Syndrome, CKD, NAFLD)
  ├── Explainability engine: Feature attribution waterfall (+/- % risk drivers)
  ├── Model provider abstraction: Google Gemini, OpenAI, and Deterministic Offline Mock provider (adapted from refactoragent)
  └── Unit tests for mathematical scoring accuracy, safety tags, and explainability output

PHASE 4: Personalized 30-Day Preventive Intervention Engine
  ├── Lifestyle medicine care-plan generator across 4 pillars (Nutrition, Physical Activity, Sleep, Stress)
  ├── 30-day daily task checklist generator and adherence tracking engine
  ├── Evidence citations linking (ICMR-NIN dietary guidelines, WHO PEN)
  └── Tests for care-plan generation, adherence calculation, and task completion

PHASE 5: Clinical Triage & Human-in-the-Loop Workflow
  ├── High-risk escalation trigger rules (critical vitals & worsening trajectories)
  ├── Clinician triage queue and AI pre-consultation SOAP summary generator
  ├── Human review state machine (PENDING, APPROVED, MODIFIED, REFERRED)
  └── Integration tests verifying clinician review approval flows

PHASE 6: Wearable Biometrics & Document Vault
  ├── Normalized timeseries biometric schemas & 7-day rolling baselines (adapted from open-wearables)
  ├── Synthetic wearable generator for the demo personas
  ├── S3/MinIO-compatible document upload and metadata indexing (adapted from bezs-filenest)
  └── Tests for wearable trend analysis and document attachment

PHASE 7: Population Health Intelligence & Epidemiological Analytics
  ├── District and PHC level aggregation queries (prevalence, risk tier distribution)
  ├── Outcome efficacy delta engine ("Did high adherence lower blood pressure/HbA1c?")
  ├── Seed data generator: 4 realistic Indian patient personas + 1,200 regional screening records
  └── Population metrics calculation tests

PHASE 8: Unified Web Portal & 5-Minute Evaluator Experience
  ├── Responsive web interface (Next.js / Tailwind / shadcn/ui components)
  ├── Citizen Portal (Screening questionnaire, Risk radar/waterfall, 30-day plan)
  ├── Clinician Portal (Triage queue, Patient trajectory, SOAP review)
  ├── Population Intelligence Dashboard (Heatmaps, Risk tiers, Outcome delta chart)
  └── Guided 5-minute interactive evaluator walkthrough demo mode

PHASE 9: Containerization, End-to-End Verification & Documentation
  ├── Dockerfile and `docker-compose.yml` for production-grade local run
  ├── End-to-end integration test suite
  └── Final deployment guide and challenge submission documentation
```

---

## 2. Verification Protocol for Each Phase

To honor the project requirement that **"Never claim functionality is implemented unless it actually runs"**, each phase will conclude with:
1. Running automated unit and integration tests.
2. Running syntax, lint, and type checks.
3. Verifying database migrations and persistence integrity.
4. Documenting changed files, test outputs, and remaining risks.
