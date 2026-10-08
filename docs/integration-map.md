# SevaHealth AI: System Integration Map & Service Topology

**Document Version:** 1.0.0  
**Target:** SevaHealth AI Platform  
**Architecture:** Microservices & Modular Monolith with Unified API Gateway

---

## 1. Network Topology & Port Allocations

The platform defines explicit networking boundaries between client applications, gateway routers, internal microservices, and persistence layers:

| Service / Container | Internal Port | Host Port | Protocol | Primary Route Prefix / Function |
|---|---|---|---|---|
| **`sevahealth-web`** | 3000 | 3000 | HTTP / Next.js | `/` (Citizen, Clinician & Admin Portals) |
| **`sevahealth-gateway`** | 8000 | 8000 | HTTP / FastAPI | `/api/v1/*`, `/docs` (Swagger UI), `/metrics` |
| **`sevahealth-postgres`** | 5432 | 5432 | TCP / Postgres | Core relational & FHIR R4 JSON storage |
| **`sevahealth-redis`** | 6379 | 6379 | TCP / Redis | Session store, rate limiting, pub/sub queue |
| **`sevahealth-minio`** | 9000, 9001 | 9000, 9001 | HTTP / S3 API | S3 object store & MinIO Web Console |

---

## 2. Service-to-Service Integration Flow

```
[Citizen Mobile / Web App]
         │
         │ HTTPS :3000 / :8000
         ▼
┌────────────────────────────────────────────────────────────────────────┐
│  API Gateway & Security Router (FastAPI :8000)                        │
│                                                                        │
│  ├── /api/v1/auth/*        ──► IAM Router (Tokens, Roles, RBAC)        │
│  ├── /api/v1/citizens/*    ──► Citizen Profile Service                 │
│  ├── /api/v1/screening/*   ──► Screening Service (CBAC, IDRS, Vitals)  │
│  ├── /api/v1/risk/*        ──► Deterministic Guidelines + AI Engine    │
│  ├── /api/v1/intervention/*──► 30-Day Care Plan Generator              │
│  ├── /api/v1/wearables/*   ──► Biometrics & Timeseries Ingestion       │
│  ├── /api/v1/clinician/*   ──► Triage Queue & Clinical Review          │
│  ├── /api/v1/documents/*   ──► Lab Report Vault (MinIO/S3)             │
│  ├── /api/v1/population/*  ──► Epidemiological Intelligence & Deltas   │
│  └── /api/v1/fhir/*        ──► HL7 FHIR R4 Interoperability Endpoints  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ AI Agent Runtime │      │ PostgreSQL 16    │      │ MinIO / S3 Vault │
│ - Gemini / Claude│      │ - Relational SQL │      │ - Encrypted lab  │
│ - Local Offline  │      │ - JSONB FHIR R4  │      │   reports, ECGs  │
│   Mock Provider  │      │ - Immutable Audit│      │ - Presigned URLs │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

---

## 3. Upstream Component Adapter Mapping

To decouple SevaHealth AI from external cloud dependencies and ensure 100% offline reproducibility:

### 3.1. AI Model Provider Adapter (`refactoragent` adaptation)
* **Interface:** `LLMClientInterface`
* **Implementations:**
  - `GeminiProvider`: Google Gemini 1.5 Pro / Flash via official Google GenAI SDK.
  - `OpenAIProvider`: OpenAI GPT-4o / GPT-4o-mini endpoint.
  - `DeterministicMockProvider` (**Default for offline evaluation**): High-fidelity, mathematically consistent mock provider that generates realistic SHAP driver explanations, 30-day intervention roadmaps, and SOAP summaries based on verified clinical guidelines—without requiring an external API key or network connection.

### 3.2. Object Storage Adapter (`bezs-filenest` adaptation)
* **Interface:** `StorageAdapterInterface`
* **Implementations:**
  - `MinioStorageAdapter`: Connects to S3/MinIO on port 9000 using `boto3` / `aiobotocore`.
  - `LocalStorageAdapter`: Emulates object storage in a local encrypted directory (`./storage_vault/`) if MinIO is not running.

### 3.3. Cache & Queue Adapter (`bezs-iam` / Redis adaptation)
* **Interface:** `CacheQueueInterface`
* **Implementations:**
  - `RedisAdapter`: Connects to Redis on port 6379 for distributed rate limiting and sliding window counters.
  - `InMemoryAdapter`: Thread-safe in-memory cache and rate limiter for single-process local runs.

### 3.4. Wearables Bridge Adapter (`open-wearables` & `DrGodly` adaptation)
* **Interface:** `WearableSyncInterface`
* **Implementations:**
  - `OpenWearablesCloudAdapter`: Ingests OAuth2 webhooks from Garmin, Oura, Fitbit.
  - `SyntheticWearableSimulator`: Generates 30-day realistic physiological timeseries (RHR, HRV, Sleep architecture, Steps) matching the four synthetic patient personas for instant live demonstration.

---

## 4. API Endpoint Contract Directory

| Route | Method | Access Role | Description |
|---|---|---|---|
| `/api/v1/auth/token` | POST | Anonymous | Authenticate with username/password, returns JWT |
| `/api/v1/auth/me` | GET | Authenticated | Return authenticated profile & role permissions |
| `/api/v1/citizens/` | GET, POST | HealthWorker, Admin | List or register new citizens |
| `/api/v1/citizens/{id}` | GET, PUT | Citizen, Clinician, HW | Get citizen profile, demographics, and ABHA ID |
| `/api/v1/screening/` | POST | Citizen, HealthWorker | Submit screening survey (CBAC/IDRS) + vitals |
| `/api/v1/risk/evaluate/{id}` | POST | Citizen, Clinician, HW | Evaluate NCD risk, trajectory & SHAP waterfall |
| `/api/v1/intervention/plan/{id}` | GET, POST | Citizen, Clinician | Generate or fetch 30-day personalized care plan |
| `/api/v1/intervention/tasks/{id}/toggle` | POST | Citizen | Check off daily lifestyle task and update adherence |
| `/api/v1/wearables/sync/{id}` | POST | Citizen, HW | Ingest smartwatch biometric timeseries |
| `/api/v1/clinician/triage` | GET | Clinician | Fetch high-risk clinician triage queue |
| `/api/v1/clinician/review/{id}` | POST | Clinician | Submit clinical review action (Approve/Modify/Refer) |
| `/api/v1/population/metrics` | GET | PublicHealthAdmin | Fetch district prevalence & intervention outcome delta |
| `/api/v1/fhir/Patient/{id}` | GET | Clinician, Admin | Export citizen record as FHIR R4 Patient JSON |
| `/api/v1/fhir/Observation` | GET, POST | Clinician, HW | Query or submit FHIR R4 Observations (LOINC coded) |
| `/health` | GET | Anonymous | System liveness probe and component health status |

---

## 5. Seeded Demo Data Strategy

On initial startup, the database automatically seeds:
1. Standard tenant organizations (`Karnataka State Health Mission` → `Mysuru District` → `Nanjangud PHC`).
2. Demo users for all 5 roles (`citizen@sevahealth.ai`, `worker@sevahealth.ai`, `doctor@sevahealth.ai`, `admin@sevahealth.ai`, `sysadmin@sevahealth.ai`).
3. The 4 realistic synthetic Indian personas (Ramesh Patel, Lakshmi Devi, Vikram Singh, Priya Sharma) pre-populated with baseline screenings, risk calculations, care plans, and longitudinal vitals.
4. Over 1,200 synthetic population screening records across 5 Karnataka districts (Mysuru, Bengaluru Rural, Hassan, Mandya, Chamarajanagar) to populate the population intelligence heatmaps and adherence-vs-outcome delta charts immediately.
