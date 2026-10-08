# SevaHealth AI

**AI-Native Preventive-Health & NCD Early-Warning Decision-Intelligence Platform**  
*Proposed for the Seva First Innovation Challenge (https://sevainnovationchallenge.in/)*  
*Problem Statement: Non-communicable and emerging lifestyle-oriented diseases*

---

## 1. Product Vision & Mission

SevaHealth AI identifies citizens who are silently progressing toward chronic disease, explains the physiological and lifestyle factors driving their risk, generates personalized preventive lifestyle medicine interventions, continuously monitors their trajectory, and escalates high-risk cases to healthcare professionals.

### The 8-Stage Core Loop
```
SCREEN ──► UNDERSTAND ──► RISK STRATIFY ──► PREDICT ──► INTERVENE ──► MONITOR ──► ESCALATE ──► MEASURE
```

### Three Stakeholder Tiers
1. **Citizen:** Mobile & web companion for guided screening, explainable risk factor breakdown, personalized 30-day preventive habit care plans, and smartwatch sync.
2. **Healthcare Worker & Clinician:** Field screening terminal for ASHA/ANM workers, high-risk triage inbox, AI pre-consultation SOAP notes, and doctor review sign-offs.
3. **Population / Public Health Administrator:** District-level epidemiological heatmaps, NCD prevalence distribution, and intervention outcome efficacy metrics.

---

## 2. Monorepo Structure

```
sevahealth-ai/
  apps/
    citizen-mobile/          # Flutter mobile application architecture & sensor specs
    clinician-web/           # Clinician decision support & triage review portal
    health-worker-web/       # ASHA / ANM field screening terminal
    public-health-web/       # District & state population intelligence dashboard

  services/
    api/                     # FastAPI Gateway & Modular Monolith orchestrator
    identity/                # IAM, OAuth 2.1 / OIDC tokens, RBAC, tenant isolation
    screening/               # CBAC & IDRS survey ingestion and calculators
    risk-engine/             # Multi-domain guideline scoring & SHAP explainability
    intervention-engine/     # 30-day personalized preventive care plan generator
    ai-agent/                # Multi-provider LLM runtime & clinical safety guardrails
    wearable/                # Biometric timeseries normalization (HR, HRV, Sleep, Steps)
    clinical/                # High-risk triage queue & doctor review sign-off
    documents/               # S3 / MinIO medical report & attachment vault
    notifications/           # Triage alerts & preventive reminder dispatcher
    population-intelligence/ # Regional epidemiological analytics & outcome delta engine

  packages/
    ui/                      # Shared design tokens and web interface components
    types/                   # Core enumerations (UserRole, RiskTier, TrajectoryTrend)
    config/                  # Pydantic v2 application settings and validator
    validation/              # Clinical bounds validation & prompt injection defenses
    clinical-models/         # LOINC observations, FHIR R4 resources, openEHR mappings
    ai-schemas/              # Typed JSON schemas for LLM reasoning & care plans
    auth/                    # JWT token creation, decoding, and role guards
    observability/           # Non-blocking async event buffer and audit logger

  infrastructure/
    docker/                  # Production & dev Dockerfiles
    postgres/                # PostgreSQL init scripts & JSONB indexes
    ehrbase/                 # openEHR REST & archetype specifications
    redis/                   # Redis session and rate limiter configurations
    object-storage/          # MinIO S3 bucket configuration
    monitoring/              # OpenTelemetry collector & metrics definitions

  ml/                        # Datasets, feature engineering, and inference pipelines
  agents/                    # Specialized preventive, clinical, and screening agents
  docs/                      # Complete system specifications & reuse analyses
  scripts/                   # Seeding scripts and end-to-end demo verification
  tests/                     # Comprehensive automated unit & integration test suites
```

---

## 3. Quickstart & Local Execution

### Option A: Direct Local Run (Zero External Dependencies)
SevaHealth AI includes built-in dual-mode storage (embedded SQLite fallback) and deterministic offline AI providers, so you can run and evaluate the complete platform locally without Docker or external cloud keys:

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Seed realistic synthetic Indian personas & regional screening data
python scripts/seed_data.py

# 3. Start the FastAPI Gateway
python -m uvicorn services.api.main:app --reload --port 8000
```
Open your browser to:
* **Interactive Web Portal:** [http://localhost:8000/](http://localhost:8000/)
* **Interactive Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **System Health Probe:** [http://localhost:8000/health](http://localhost:8000/health)

### Option B: Containerized Run (Docker Compose)
```bash
docker compose up --build -d
```

---

## 4. Automated Testing & Verification

Run the complete test suite:
```bash
pytest tests -v
```

Run the end-to-end 8-stage core loop demo verification:
```bash
python scripts/test_e2e.py
```

---

## 5. The 5-Minute Challenge Evaluator Flow

When opening [http://localhost:8000/](http://localhost:8000/), an evaluator can verify the platform end-to-end in 5 minutes:

1. **Step 1: Select Citizen** &rarr; Select pre-seeded persona *Ramesh Patel* (48M, Bengaluru Rural).
2. **Step 2: Preventive Screening** &rarr; Inspect pre-populated CBAC and IDRS (60/100, High Risk) surveys.
3. **Step 3: Multi-Factor Risk Assessment** &rarr; View composite risk (*HIGH: 61%*), prediabetes probability (*65%*), and prehypertension risk (*60%*).
4. **Step 4: Explainability Waterfall** &rarr; Understand top drivers: *+22% Impaired Glycemia (HbA1c 6.2%)*, *+18% Vascular Pressure (138/88 mmHg)*, and protective factors (*-15% Tobacco Abstinence*). Notice the clear safety disclaimer: *"Clinical review recommended"*.
5. **Step 5: 30-Day Preventive Care Plan** &rarr; Review tailored nutrition guidance (swapping white rice with foxtail millet/ragi) and click to check off daily habit tasks, watching adherence update live.
6. **Step 6: Wearable Biometrics Sync** &rarr; Click "Sync Wearables" to ingest 14 days of normalized smartwatch telemetry (Resting HR, HRV, sleep stages, daily steps).
7. **Step 7: Clinician Triage Review** &rarr; Switch to the Clinician tab. Review *Lakshmi Devi* (escalated for Stage 2 HTN 164/98 mmHg), inspect the AI-drafted pre-consult SOAP note, and click **"Doctor Sign-off & Approve Care Plan"**.
8. **Step 8: Population Intelligence** &rarr; Switch to the Population Health tab. View district heatmaps and verify the **Outcome Efficacy Delta**: Citizens with &ge;75% adherence achieved an average **-6.4 mmHg systolic BP drop** and **-14.2 mg/dL fasting glucose reduction** over 30 days!

---

## 6. Clinical Safety & Governance

SevaHealth AI is strictly non-diagnostic:
* **AI may:** Stratify preventive risk, explain physiological drivers, formulate lifestyle medicine habits, summarize pre-consult history, and flag critical thresholds.
* **AI must NOT:** Autonomously diagnose disease, prescribe pharmaceutical medications, titrate dosages, or issue medical orders.
* **Human-in-the-Loop:** All escalated cases require licensed physician sign-off. Probabilistic risk is never presented as a confirmed medical condition.

---

## 7. Open-Source Reuse & Attribution Matrix

In compliance with open-source licensing, all eleven upstream reference repositories are documented in [`docs/REUSE_MATRIX.md`](docs/REUSE_MATRIX.md) and [`docs/repository-reuse-analysis.md`](docs/repository-reuse-analysis.md). No copyright notices have been removed:

* `bezs-iam` (MIT, Yazhnimalan) &rarr; Adapted for RBAC, JWT tokens, and audit schemas.
* `bezs-filenest` (MIT, Yazhnimalan) &rarr; Adapted for S3/MinIO presigned medical report vault.
* `bezs-pipeline` (MIT, alphaesAI) &rarr; Adapted for tabular screening validation pipelines.
* `refactoragent` (MIT-compatible) &rarr; Adapted for clinical prompt structuring, safety barriers, and multi-provider LLM abstractions.
* `bezs-hms` (MIT, Yazhnimalan) &rarr; Adapted for clinician triage queue and consultation review patterns.
* `DrGodly-Mobile-Aplication` (Saythu000) &rarr; Referenced for mobile intake UX and BLE/Health Connect sensor matrix.
* `ehrbase` (Apache-2.0, openEHR Foundation) &rarr; Referenced for clinical archetype rigor.
* `bezs-emr-gql` (MIT, Yazhnimalan) &rarr; Reused for LOINC terminology and FHIR R4 Pydantic schemas.
* `bezs-emr-mcp` (MIT, Yazhnimalan) &rarr; Adapted for AI agent clinical tool contracts.
* `bezs-observability` (MIT, Yazhnimalan) &rarr; Adapted for async event buffer and telemetry middleware.
* `open-wearables` (MIT, Momentum) &rarr; Reused for normalized biometric timeseries schemas and recovery algorithms.
