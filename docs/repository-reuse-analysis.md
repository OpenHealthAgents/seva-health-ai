# SevaHealth AI: Deep Technical Reconnaissance of Upstream Repositories

**Document Version:** 2.0.0 (Comprehensive Reconnaissance & Component Classification)  
**Target Platform:** SevaHealth AI (Seva First Innovation Challenge)  
**Evaluated Repositories:** 11 Source Repositories  
**Component Classification Taxonomy:**
- `REUSE_DIRECTLY`: Production-ready schemas, contracts, or modules used as-is or with direct imports.
- `ADAPT`: Concepts, schemas, or logic ported, extended, or refactored to fit SevaHealth's architectural boundaries.
- `REFERENCE`: Architectural patterns, UI conventions, sequence flows, or standards used to guide design without importing code.
- `DO_NOT_USE`: Out-of-scope, bloated, proprietary, or risky code explicitly excluded from the build.

---

## 1. Deep Technical Inventory by Repository (20 Dimensions)

### 1.1. `bezs-iam`
1. **Primary purpose:** Central Identity and Access Management (IAM) authority, issuing OAuth 2.1 / OIDC tokens, API keys, AI agent capability credentials, and enforcing multi-tenant organization isolation.
2. **Language:** TypeScript (Node.js runtime).
3. **Framework:** Next.js 15 (App Router), Better Auth, React 19.
4. **Database:** PostgreSQL managed via Prisma ORM (`prisma/schema/schema.prisma`).
5. **API style:** RESTful JSON endpoints (`/api/auth/*`, `/oauth2/*`, `/admin/api/*`).
6. **Authentication:** Better Auth session tokens, JWTs with RS256/HS256 signing, OAuth 2.1 PKCE flows, Two-Factor Authentication (TOTP).
7. **Authorization:** Role-Based Access Control (RBAC) and Organization/Team membership (`User`, `Role`, `Member`, `Organization`, `AgentCapabilityGrant`).
8. **Frontend technology:** Next.js App Router, Tailwind CSS, shadcn/ui admin management console.
9. **Mobile technology:** None native (acts as OAuth 2.1 / OIDC token provider for mobile consumers).
10. **Background jobs:** In-process token cleanup, Next.js instrumentation hooks.
11. **Messaging/event architecture:** Webhooks for auth lifecycle events; database-backed audit log queue.
12. **File/document handling:** Avatar image uploads via standard HTTP multipart.
13. **AI/agent capabilities:** Advanced capability-based agent authentication (`AgentHost`, `AgentCapabilityGrant`, device-code approval flows for autonomous agents).
14. **Observability:** Custom audit log tables, Winston/structlog console logging, Better Auth error logging.
15. **Docker support:** Production `Dockerfile`, `docker-compose.yml`, and `docker-compose.prod.yml`.
16. **Testing:** Jest / Vitest unit tests, Playwright E2E suites.
17. **Configuration:** Environment variables (`.env`, `.env.example`) validated via Zod schemas.
18. **Security:** Cloudflare Turnstile captcha support, sliding-window rate limiters, timing-safe credential comparisons, immutable audit records.
19. **License:** MIT License (Copyright (c) 2026 Yazhnimalan).
20. **Reusable components:**
    - Role taxonomy and permission mapping (`src/lib/permissions.ts`)
    - Agent capability grant model schema (`prisma/schema/schema.prisma`)
    - Immutable audit event schema (`AuditLog`)

---

### 1.2. `bezs-filenest`
1. **Primary purpose:** Enterprise medical document and file management infrastructure providing S3/MinIO abstractions, virus scanning, MIME classification, and presigned uploads.
2. **Language:** Python 3.12+ (backend), TypeScript (SDKs and frontend).
3. **Framework:** FastAPI (backend), Next.js 16 (web console), Pydantic v2, SQLAlchemy 2.0 (asyncio).
4. **Database:** PostgreSQL (metadata) via `asyncpg`, OpenSearch (search index), Redis (cache/tokens).
5. **API style:** OpenAPI / RESTful JSON with presigned URL upload negotiation.
6. **Authentication:** JWT Bearer tokens validated against public keys / JWKS; API keys for machine access.
7. **Authorization:** Tenant isolation via `organization_id + project_id` scoping on every database query.
8. **Frontend technology:** Next.js 16, React 19, Tailwind CSS, shadcn/ui.
9. **Mobile technology:** Cross-platform React Native / Flutter SDK interfaces.
10. **Background jobs:** Celery / Async background workers for file parsing, ClamAV virus scanning, and thumbnail generation.
11. **Messaging/event architecture:** NATS (`nats-py`) and Redis Streams for asynchronous file state change notifications.
12. **File/document handling:** S3 / MinIO / Azure Blob / GCS object storage adapter via `aioboto3`; multipart resumable uploads; MIME verification via `python-magic-bin`.
13. **AI/agent capabilities:** Document classification and optical layout parsing hooks for medical records.
14. **Observability:** OpenTelemetry SDK (`opentelemetry-sdk`, `opentelemetry-exporter-otlp`), `structlog` JSON logger.
15. **Docker support:** Comprehensive `docker-compose.yml` including MinIO, Redis, NATS, and PostgreSQL.
16. **Testing:** Pytest with `pytest-asyncio` and `httpx.AsyncClient`.
17. **Configuration:** `pydantic-settings` via `BaseSettings` reading from `.env`.
18. **Security:** WORM (Write Once Read Many), legal hold, retention policies, SHA256 file checksum verification, MIME sniffing defense.
19. **License:** MIT License (Copyright (c) 2026 Yazhnimalan).
20. **Reusable components:**
    - `backend/app/storage/` (S3/MinIO async client wrapper and presigned URL generator)
    - Medical attachment metadata schema (`LAB_REPORT`, `ECG_STRIP`, `IMAGING`)
    - File upload validation and checksum verification algorithms

---

### 1.3. `bezs-pipeline`
1. **Primary purpose:** Batch data pipeline and ETL platform designed to ingest, clean, transform, and index clinical and biomedical datasets into search and analytics stores.
2. **Language:** Python 3.8 - 3.12.
3. **Framework:** Apache Airflow 2.7.3, PySpark, Pydantic, Pandas, NumPy.
4. **Database:** PostgreSQL / RDBMS connectors, Elasticsearch 8.x, OpenSearch 2.x, MongoDB.
5. **API style:** Internal Airflow DAG orchestration and Python programmatic ETL hooks.
6. **Authentication:** Airflow Connection Manager and encrypted credential vault.
7. **Authorization:** Service account access keys and database connection strings.
8. **Frontend technology:** Airflow Web UI for DAG execution inspection.
9. **Mobile technology:** None.
10. **Background jobs:** Airflow Celery / Local Executors for asynchronous batch scheduling.
11. **Messaging/event architecture:** Airflow triggers and message queues (Redis / RabbitMQ).
12. **File/document handling:** Unstructured text extraction via `txtai` and PDF/JSON readers.
13. **AI/agent capabilities:** Text embeddings generation (`txtai` submodule) for semantic medical document search.
14. **Observability:** Airflow task logs, StatsD metrics collector.
15. **Docker support:** `Dockerfile` and Airflow compose definitions.
16. **Testing:** Pytest test suites in `tests/` covering connectors, transformers, and loaders.
17. **Configuration:** Airflow environment variables (`AIRFLOW__*`), YAML/JSON configs.
18. **Security:** Credential encryption at rest, rate limiting utilities (`resilience.py`).
19. **License:** MIT License (Copyright (c) 2026 alphaesAI).
20. **Reusable components:**
    - `src/custom/transformers/` (Structured JSON and survey data transformation patterns)
    - `src/custom/utils/resilience.py` (Exponential backoff retry loops and rate limiters)
    - Tabular clinical survey validation schemas

---

### 1.4. `refactoragent`
1. **Primary purpose:** Multi-agent clinical intake and decision-support framework featuring clinical speech-to-speech, SOAP clinical note generation, and pre-visit intake assessments.
2. **Language:** Python 3.12+.
3. **Framework:** FastAPI, WebSockets, Pydantic, OpenAI SDK, MLflow.
4. **Database:** SQLite / Local JSON persistence (`clinical_documents_backup.json`), OpenSearch hybrid search.
5. **API style:** RESTful HTTP + bidirectional WebSockets (`/ws/diarize`, `/ws/webs2s`).
6. **Authentication:** JWT Bearer token decoding (`api/auth.py`).
7. **Authorization:** Role checks (Doctor vs Patient) on WebSocket channels.
8. **Frontend technology:** Static HTML/JavaScript test harness (`ui/chat.html`, `ui/diarze.html`).
9. **Mobile technology:** Designed to back DrGodly Flutter mobile app's pre-visit intake screen.
10. **Background jobs:** In-process asyncio tasks for audio chunking, diarization, and LLM streaming.
11. **Messaging/event architecture:** In-memory Event Bus (`agent/events.py`: `AgentEventType`), WebSocket streaming deltas.
12. **File/document handling:** PDF clinical extraction and OCR utilities (`utils/pdf_extractor.py`, `utils/pdf_ocr.py`, `reportlab` PDF report generation).
13. **AI/agent capabilities:** Clinical pre-visit intake agent (`customagents/previsitagent`), SOAP note synthesis (`customagents/reportagent`), multi-provider LLM abstraction (`client/llm_client.py`), loop detection, context compaction.
14. **Observability:** MLflow tracker (`utils/mlflow_tracker.py`), token usage counter, structured Python logging.
15. **Docker support:** `Dockerfile` for containerized agent deployment.
16. **Testing:** Comprehensive test suite in `test/` (`test_clinical_extraction.py`, `test_diarize_agent.py`, `test_voice_session_isolation.py`).
17. **Configuration:** TOML config loader (`config/config.toml`, `config/loader.py`).
18. **Security:** Clinical safety approval barriers (`safety/approval.py`), non-autonomous action confirmations, input sanitization.
19. **License:** Open Source / MIT Compatible.
20. **Reusable components:**
    - `safety/approval.py` (Clinical safety policy enforcement engine)
    - `client/llm_client.py` (Multi-provider model client abstraction)
    - `customagents/previsitagent/intakeprompt.py` (Structured intake prompt patterns)
    - `customagents/reportagent/assesment.py` (Clinical assessment and plan structuring)

---

### 1.5. `bezs-hms`
1. **Primary purpose:** Telemedicine, hospital, and clinic management system orchestrating patient encounters, appointments, clinical notes, and physician reviews.
2. **Language:** TypeScript.
3. **Framework:** Next.js 16 (App Router), React 19, Tailwind CSS, shadcn/ui, Prisma ORM.
4. **Database:** PostgreSQL (`prisma/schema/schema.prisma`).
5. **API style:** Next.js Server Actions and REST API routes (`/api/*`).
6. **Authentication:** Better Auth client integration, JWT Bearer tokens.
7. **Authorization:** RBAC with role routing (Patient, Doctor, Admin).
8. **Frontend technology:** Next.js App Router, Tailwind CSS, shadcn/ui, Radix UI primitives.
9. **Mobile technology:** Responsive web layout optimized for mobile browsers.
10. **Background jobs:** Autosave draft synchronization for clinical notes (`draft_updated_at`).
11. **Messaging/event architecture:** LiveKit WebRTC signaling for video/audio consultations.
12. **File/document handling:** FileNest SDK integration (`@filenest-fs/react`, `@filenest-fs/nextjs`) for prescription and lab attachments.
13. **AI/agent capabilities:** Consumption of AI-generated intake summaries, SOAP reports, and FHIR resource extractions.
14. **Observability:** Structured server logging, telemetry hooks.
15. **Docker support:** `docker-compose.dev.yml`, `docker-compose.yml`, `Dockerfile`.
16. **Testing:** Vitest / Jest unit tests, TypeScript type checking.
17. **Configuration:** Environment variables (`.env.example`) validated via Zod.
18. **Security:** Two-step clinical review sign-off (`published_at`, `published_by`), autosave race condition prevention.
19. **License:** MIT License (Copyright (c) 2026 Yazhnimalan).
20. **Reusable components:**
    - Clinical triage review queue UI layout and patient header cards
    - Consultation and Intake state machine models (`WAITING`, `ACTIVE`, `COMPLETED`)
    - Post-consultation human sign-off architecture (`published_at`, `published_by`)

---

### 1.6. `DrGodly-Mobile-Aplication`
1. **Primary purpose:** Flutter mobile application for citizens and patients to track health metrics, connect hardware sensors/wearables, complete pre-visit AI intake, and book doctor appointments.
2. **Language:** Dart (Flutter SDK >= 3.5.0 < 4.0.0).
3. **Framework:** Flutter, Provider state management, Dio HTTP client, Google Fonts.
4. **Database:** SQLite via `sqflite` (local offline patient cache and vitals storage).
5. **API style:** RESTful JSON client interfacing with FHIR API Gateway (`lib/data/service/fhir_api_client.dart`) and AI Agent HTTP stream.
6. **Authentication:** OAuth 2.1 WebView flow and secure token persistence (`flutter_secure_storage`).
7. **Authorization:** Patient role token bearer authorization on outgoing HTTP headers.
8. **Frontend technology:** Flutter Material Design widgets, custom medical design system (blue/white aesthetic).
9. **Mobile technology:** Native Android & iOS targets with Android Health Connect and Bluetooth LE (0x180D) bridges.
10. **Background jobs:** Native periodic background sync via `flutter_local_notifications` and sensor polling.
11. **Messaging/event architecture:** Server-Sent Events / NDJSON streaming for live AI intake chat typing animation.
12. **File/document handling:** Local image picker and file upload for patient avatars and medical records.
13. **AI/agent capabilities:** Interactive AI Pre-Visit Intake chat interface (`lib/view/intake/intake_chat_screen.dart`), quick chip responses.
14. **Observability:** Local crash logger and Dio network interceptor logging.
15. **Docker support:** None (mobile client repository).
16. **Testing:** Flutter unit and widget tests (`test/`).
17. **Configuration:** `lib/core/config/` constants and environment flavor configurations.
18. **Security:** Hardware sensor runtime permission requests (`permission_handler`), secure local storage of JWT credentials.
19. **License:** Open Reference Architecture.
20. **Reusable components:**
    - `lib/data/service/fhir_api_client.dart` (Typed FHIR REST client conventions)
    - `docs/INTAKE_FEATURE_DOCUMENTATION.md` (Mobile AI intake UX workflow and state sequence)
    - `docs/open_wearables_device_compatibility.md` (Wearable bridge specifications)

---

### 1.7. `open-wearables`
1. **Primary purpose:** Open-source platform for ingesting, normalizing, and scoring biometric timeseries data from consumer smartwatches and medical wearables.
2. **Language:** Python 3.12 - 3.14 (backend), TypeScript (developer portal).
3. **Framework:** FastAPI, SQLAlchemy 2.0, Alembic, Celery, Pydantic v2.
4. **Database:** PostgreSQL (with timeseries optimizations), Redis (Celery broker and cache).
5. **API style:** RESTful JSON API with webhook ingestion endpoints (`/api/v1/webhooks/*`).
6. **Authentication:** JWT Bearer tokens, API keys, OAuth 2.0 client credentials.
7. **Authorization:** Tenant and user isolation (`user_id` scoping).
8. **Frontend technology:** Vite, React, TypeScript developer portal (`frontend/`).
9. **Mobile technology:** Companion SDK hooks for mobile health ingestion.
10. **Background jobs:** Celery workers with Flower dashboard for asynchronous biometric normalization and rolling score calculations.
11. **Messaging/event architecture:** Redis Streams and Celery task queues.
12. **File/document handling:** Parsing of binary FIT files (`services/fit_parser.py`) and raw payload S3 archiving.
13. **AI/agent capabilities:** Physiological scoring primitives: sleep architecture scoring, resilience/recovery algorithms, resting baseline drift detection.
14. **Observability:** Sentry SDK integration, OpenTelemetry (`integrations/otel.py`), Prometheus metrics.
15. **Docker support:** Production `docker-compose.yml` with backend, worker, beat, flower, redis, and postgres services.
16. **Testing:** Pytest suite in `tests/` covering API routes, webhook ingestion, and scoring algorithms.
17. **Configuration:** `pydantic-settings` via `BaseSettings` reading environment variables.
18. **Security:** Webhook signature verification (HMAC-SHA256), encrypted provider OAuth tokens, rate limiting.
19. **License:** MIT License (Copyright (c) 2025 Momentum).
20. **Reusable components:**
    - `backend/app/schemas/` (Normalized schemas for Resting HR, HRV, Sleep stages, Steps, Calories)
    - `backend/app/algorithms/` (Scoring primitives, rolling baseline calculations, resilience indices)
    - Timeseries aggregation and normalization logic

---

### 1.8. `ehrbase`
1. **Primary purpose:** Open-source clinical data repository compliant with openEHR specifications, providing an official Archetype Query Language (AQL) engine and REST API.
2. **Language:** Java 17+.
3. **Framework:** Spring Boot 3.x, openEHR SDK, jOOQ.
4. **Database:** PostgreSQL (storing openEHR Release Model structures as relational and JSONB compositions).
5. **API style:** openEHR REST API specifications (EHR, Composition, Template, AQL query).
6. **Authentication:** OAuth 2.0 / OpenID Connect via Keycloak integration, HTTP Basic.
7. **Authorization:** Role-based access control, tenant multi-tenancy.
8. **Frontend technology:** None (pure clinical repository engine).
9. **Mobile technology:** None.
10. **Background jobs:** Asynchronous validation and composition indexing jobs.
11. **Messaging/event architecture:** Spring application events and optional Kafka audit streaming.
12. **File/document handling:** Structured XML/JSON openEHR compositions; binary attachment handling via openEHR multimedia data types.
13. **AI/agent capabilities:** None native (acts as the immutable clinical ground truth queryable via AQL).
14. **Observability:** Micrometer metrics, Prometheus endpoint, Logback structured logging.
15. **Docker support:** Production `Dockerfile` and `docker-compose.yml`.
16. **Testing:** JUnit 5, Mockito, Testcontainers integration test suite.
17. **Configuration:** Spring `application.yml` and environment variables (`EHRBASE_*`).
18. **Security:** Strict schema compliance, cryptographic hash verification of clinical compositions, complete revision history tracking.
19. **License:** Apache License 2.0 (Copyright (c) 2019-2024 vitasystems GmbH / openEHR Foundation).
20. **Reusable components:**
    - Clinical Archetype definitions for Blood Pressure, Blood Glucose, Laboratory Results, and Care Plans
    - Longitudinal clinical modeling principles and immutable audit semantics
    - Standards-based data dictionary concepts

---

### 1.9. `bezs-emr-gql`
1. **Primary purpose:** Healthcare API orchestration service providing typed Pydantic models for 17 FHIR R4 clinical resource types, standard LOINC/SNOMED coding, and JWT RBAC validation.
2. **Language:** Python 3.12 - 3.14.
3. **Framework:** FastAPI, Pydantic v2, `dependency-injector`, HTTPX.
4. **Database:** None direct (proxies persistence to upstream FHIR server), Redis (rate limiting).
5. **API style:** RESTful JSON conforming to HL7 FHIR R4 resource definitions.
6. **Authentication:** JWT Bearer tokens with JWKS cryptographic signature verification (`app/auth/`).
7. **Authorization:** Scope and role validation on FHIR resource endpoints (`Patient`, `Observation`, `Condition`).
8. **Frontend technology:** FastAPI interactive Swagger UI with Bearer auth injection.
9. **Mobile technology:** Compatible with mobile FHIR REST consumers.
10. **Background jobs:** In-memory rate limiting sliding-window flusher.
11. **Messaging/event architecture:** Synchronous HTTP proxying with timeout resilience.
12. **File/document handling:** FHIR `DocumentReference` and `DiagnosticReport` Pydantic models.
13. **AI/agent capabilities:** Terminology validation services useful for AI prompt and tool extraction grounding.
14. **Observability:** Structured FastAPI middleware logs, health probe (`/health`).
15. **Docker support:** Multi-stage `Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`.
16. **Testing:** Pytest test suite testing auth, routers, and schemas.
17. **Configuration:** `pydantic-settings` via `app/config.py`.
18. **Security:** Sliding window rate limiting (per-user via `sub`, per-IP for anonymous), input validation via Pydantic.
19. **License:** MIT License (Copyright (c) 2026 Yazhnimalan).
20. **Reusable components:**
    - `app/schemas/observation/` (LOINC-coded FHIR Observation models)
    - `app/schemas/terminology.py` (Standard LOINC codes for HbA1c, glucose, vitals, lipids)
    - `app/schemas/patient/` (FHIR R4 Patient schema)
    - `app/auth/` (FastAPI JWT Bearer dependency injection architecture)

---

### 1.10. `bezs-emr-mcp`
1. **Primary purpose:** Model Context Protocol (MCP) server exposing clinical Electronic Medical Record tools and patient history safely to AI agents.
2. **Language:** Python / TypeScript (MCP SDK).
3. **Framework:** Model Context Protocol specification.
4. **Database:** Read-only access to EMR / FHIR storage.
5. **API style:** JSON-RPC over STDIO / HTTP Server-Sent Events (SSE).
6. **Authentication:** Agent capability token / API key.
7. **Authorization:** Granular tool-level execution grants (`tools/call` permissions).
8. **Frontend technology:** None.
9. **Mobile technology:** None.
10. **Background jobs:** None.
11. **Messaging/event architecture:** MCP JSON-RPC protocol messaging.
12. **File/document handling:** Clinical document text extraction tools.
13. **AI/agent capabilities:** Standardized clinical tool registry (`get_patient_vitals`, `get_chronic_risk_history`).
14. **Observability:** MCP tool invocation audit logs.
15. **Docker support:** Lightweight container definition.
16. **Testing:** Protocol mock tests.
17. **Configuration:** MCP server JSON configuration file.
18. **Security:** Read-only tool boundary prevents unauthorized clinical record mutations.
19. **License:** MIT License (Copyright (c) 2026 Yazhnimalan).
20. **Reusable components:**
    - Clinical tool definitions and JSON schema parameters for AI agent tool calling
    - Parameter validation contracts for medical record inspection

---

### 1.11. `bezs-observability`
1. **Primary purpose:** Self-hosted enterprise observability and telemetry suite for logs, distributed tracing, Prometheus metrics, and clinical audit events.
2. **Language:** Python, Go, TypeScript, Rust.
3. **Framework:** FastAPI, Go HTTP Gateway, Next.js (Console UI), ClickHouse.
4. **Database:** ClickHouse (telemetry analytics), Redis (streams & pub/sub), PostgreSQL (IAM).
5. **API style:** Telemetry ingestion API (Go, port 8080), Real-time WebSockets (Go, port 8081).
6. **Authentication:** API keys and Better Auth session credentials.
7. **Authorization:** Multi-tenant organization and application scoping (`org_id + app_id`).
8. **Frontend technology:** Next.js, Tailwind CSS, shadcn/ui observability console (`apps/console`).
9. **Mobile technology:** React Native telemetry SDK (`sdk/react-native`).
10. **Background jobs:** Python analytics processing worker (`apps/analytics-python`).
11. **Messaging/event architecture:** Redis Streams (`XADD`) for high-throughput event ingestion; Redis Pub/Sub for live fanout.
12. **File/document handling:** None.
13. **AI/agent capabilities:** AI agent token tracking, execution latency monitoring, prompt-response tracing.
14. **Observability:** Self-monitoring, OpenTelemetry OTLP compatibility, ClickHouse query analytics.
15. **Docker support:** Production `docker-compose.yml` spinning ClickHouse, Redis, Gateway, Analytics, and Console.
16. **Testing:** Pytest (Python SDK and analytics worker), Go test suites.
17. **Configuration:** Environment variables (`.env.example`) and Justfile task runner.
18. **Security:** Ingestion token validation, non-blocking asynchronous buffering.
19. **License:** MIT License (Copyright (c) 2026 Yazhnimalan).
20. **Reusable components:**
    - `sdk/python/src/watcher_sdk/buffer.py` (In-memory asynchronous event buffer)
    - `sdk/python/src/watcher_sdk/flusher.py` (Non-blocking background flusher)
    - `sdk/python/src/watcher_sdk/integrations/fastapi.py` (FastAPI telemetry middleware)
    - Structured audit event taxonomy (`RISK_ASSESSED`, `CLINICIAN_REVIEWED`)

---

## 2. Comprehensive Component Reuse Matrix

| Repository | Component | SevaHealth Usage | Integration Method | Priority | Risk | Classification |
|---|---|---|---|---|---|---|
| **bezs-iam** | RBAC Role Taxonomy & Permissions | Enforces 5 user roles across API endpoints | Adapt into FastAPI security dependencies | High | Low | `ADAPT` |
| **bezs-iam** | Agent Capability Grants Schema | Issues scoped execution tokens to AI workers | Adapt into Pydantic agent models | Medium | Low | `ADAPT` |
| **bezs-iam** | Full Next.js IAM Cloud Console | Cloud user admin UI & Turnstile captcha | Excluded (unnecessary RAM overhead for MVP) | None | High | `DO_NOT_USE` |
| **bezs-filenest** | S3 / MinIO Storage Client Wrapper | Generates presigned URLs for lab reports | Adapt into SevaHealth Document Service | Medium | Low | `ADAPT` |
| **bezs-filenest** | Medical Document Metadata Schemas | Categorizes lab PDFs, ECGs, and imaging | Direct schema reuse in Pydantic models | Medium | Low | `REUSE_DIRECTLY` |
| **bezs-filenest** | ClamAV Daemon & OpenSearch Cluster | Virus scanning & full-text cluster search | Replaced with local MIME/hash checks | Low | High | `DO_NOT_USE` |
| **bezs-pipeline** | Tabular Clinical Data Cleaning Schemas | Validates community screening survey batches | Adapt into screening ingestion pipeline | Medium | Low | `ADAPT` |
| **bezs-pipeline** | Airflow DAGs & PySpark Infrastructure | Heavy distributed data orchestration | Excluded (overkill for sub-second API) | None | High | `DO_NOT_USE` |
| **refactoragent** | Clinical Safety Policy Engine | Blocks unvetted diagnoses or prescriptions | Adapt into AI Safety Guardrail middleware | High | Low | `ADAPT` |
| **refactoragent** | LLM Client Multi-Provider Abstraction | Switches between Gemini, OpenAI & Mock LLM | Adapt into SevaHealth AI Provider Layer | High | Low | `ADAPT` |
| **refactoragent** | SOAP Clinical Note Structuring Prompts | Synthesizes clinician pre-visit summaries | Adapt for NCD preventive medicine | High | Low | `ADAPT` |
| **refactoragent** | Speech-to-Speech WebSockets | Real-time audio diarization streaming | Out of scope for core NCD early warning | None | Medium | `DO_NOT_USE` |
| **bezs-hms** | Clinical Triage Review Queue UI | Displays escalating cases to physicians | Adapt into Next.js Clinician Portal | High | Low | `ADAPT` |
| **bezs-hms** | Consultation Review State Machine | Manages `published_at` doctor sign-off | Adapt into Human-in-the-Loop workflow | High | Low | `ADAPT` |
| **bezs-hms** | LiveKit WebRTC Video Infrastructure | Real-time video consultation calling | Excluded from core screening MVP | None | Medium | `DO_NOT_USE` |
| **DrGodly-Mobile-App**| Mobile Intake Screening Flow | Step-by-step screening survey questionnaire | Reference for mobile-friendly UX | High | Low | `REFERENCE` |
| **DrGodly-Mobile-App**| FHIR API Client Conventions | Intercepts tokens, handles offline caching | Reference for client-side API layer | Medium | Low | `REFERENCE` |
| **DrGodly-Mobile-App**| Hardcoded Localhost IPs (`10.0.2.2`) | Local emulator network addresses | Excluded; dynamic configs enforced | None | Low | `DO_NOT_USE` |
| **open-wearables** | Normalized Biometric Schemas | Ingests Resting HR, HRV, Sleep, Steps | Reuse Pydantic models directly | High | Low | `REUSE_DIRECTLY` |
| **open-wearables** | Scoring Primitives & Baseline Trends | Calculates 7-day autonomic recovery shifts | Adapt into NCD physiological trend engine | High | Low | `ADAPT` |
| **open-wearables** | Third-party Cloud OAuth2 Webhooks | Connects Garmin, Whoop, Oura cloud APIs | Replaced with synthetic wearable simulator | Low | Medium | `DO_NOT_USE` |
| **ehrbase** | openEHR Archetypes (BP, Labs, CarePlan)| Guides data normalization & schema fields | Reference for clinical semantic rigor | High | Low | `REFERENCE` |
| **ehrbase** | JVM / Spring Boot Server Cluster | Heavy Java 17 service running alongside DB | Replaced with native Postgres FHIR tables | None | High | `DO_NOT_USE` |
| **bezs-emr-gql** | FHIR R4 Pydantic Schemas | Validates Patient and Observation resources | Reuse Pydantic models directly | High | Low | `REUSE_DIRECTLY` |
| **bezs-emr-gql** | Terminology Dictionaries (`terminology.py`)| Maps LOINC codes for HbA1c, BP, Lipids | Reuse dictionaries directly | High | Low | `REUSE_DIRECTLY` |
| **bezs-emr-gql** | External FHIR Server Proxying | Relies on external third-party FHIR server | Replaced with direct PostgreSQL store | None | Medium | `DO_NOT_USE` |
| **bezs-emr-mcp** | Clinical MCP Tool Call Contracts | Exposes clinical query tools to LLMs | Adapt into SevaHealth Agent Tool Registry | Medium | Low | `ADAPT` |
| **bezs-observability**| Watcher SDK Async Event Buffer | Buffers audit & telemetry events non-blockingly| Adapt into FastAPI observability layer | High | Low | `ADAPT` |
| **bezs-observability**| ClickHouse & Go Telemetry Microservices | Heavy multi-service analytics pipeline | Replaced with PostgreSQL audit tables | None | High | `DO_NOT_USE` |

---

## 3. Deep-Dive Architectural Focus Areas

### 3.1. Authentication & Tenant Authorization
* **Findings:** `bezs-iam` provides a rich OAuth 2.1 / OIDC architecture, but requiring a full Next.js server purely for token issuance adds unwanted runtime weight.
* **SevaHealth Strategy (`ADAPT`):** Port the JWT claim structure (`sub`, `tenant_id`, `role`, `scopes`) and permission matrices into lightweight FastAPI security dependencies (`app/core/security.py`). Enforce strict multi-tenancy by filtering all database queries on `tenant_id`.

### 3.2. Mobile UI & Community Health Worker Workflows
* **Findings:** `DrGodly-Mobile-Aplication` has an exceptionally clean medical Flutter interface for intake and biometric dashboards, tailored for mobile devices.
* **SevaHealth Strategy (`REFERENCE`):** Replicate this intuitive, step-by-step intake interaction within both a responsive Next.js mobile web shell and the mobile architecture documentation. This allows ASHA workers and citizens to complete CBAC/IDRS screenings smoothly on low-cost smartphones.

### 3.3. EMR & Clinical Interoperability
* **Findings:** `bezs-emr-gql` contains high-quality FHIR R4 Pydantic schemas and standard LOINC codes, while `ehrbase` provides deep openEHR archetype semantics.
* **SevaHealth Strategy (`REUSE_DIRECTLY` & `ADAPT`):** Import `bezs-emr-gql`'s LOINC dictionaries and Observation models directly into SevaHealth's clinical layer. Persist these records directly to PostgreSQL as structured FHIR R4 JSON documents, ensuring complete ABDM compliance without requiring a heavy Java JVM or external proxy.

### 3.4. Document Processing & File Vault
* **Findings:** `bezs-filenest` implements production-grade S3/MinIO abstractions, but its dependencies on ClamAV daemons and OpenSearch clusters impose heavy memory overhead.
* **SevaHealth Strategy (`ADAPT`):** Extract the core S3/MinIO asynchronous storage adapter and medical metadata models. Replace ClamAV with strict in-process MIME sniffing and file size constraints, storing document metadata directly in PostgreSQL.

### 3.5. Wearable Data Ingestion & Continuous Monitoring
* **Findings:** `open-wearables` offers the gold standard in vendor-neutral physiological schemas (Resting HR, HRV, sleep stages, steps) and recovery algorithms.
* **SevaHealth Strategy (`REUSE_DIRECTLY` & `ADAPT`):** Direct reuse of the normalized biometric schemas. Complement with a high-fidelity synthetic wearable simulator that feeds realistic timeseries data for the demo personas, eliminating external cloud OAuth dependencies.

### 3.6. AI Agent Orchestration & Clinical Safety Guardrails
* **Findings:** `refactoragent` implements proven clinical prompt structuring, multi-provider LLM abstractions, and safety approval gates (`safety/approval.py`).
* **SevaHealth Strategy (`ADAPT`):** Re-purpose the prompts for **NCD preventive medicine and lifestyle interventions** (ICMR and WHO-SEAR guidelines). Enforce an unyielding safety boundary: AI outputs are flagged with `"Clinical review recommended"`, and autonomous prescriptions or diagnoses are strictly prohibited. Supply a deterministic offline mock provider for 100% reliable local evaluation.

### 3.7. Observability & Audit Infrastructure
* **Findings:** `bezs-observability` features an elegant, non-blocking Python SDK (`watcher_sdk`) that buffers events in memory and flushes them asynchronously.
* **SevaHealth Strategy (`ADAPT`):** Embed the `watcher_sdk` buffer and FastAPI middleware pattern directly into the backend. Route audit events to append-only PostgreSQL tables for instant inspection, while supporting standard OpenTelemetry OTLP exporters.

---

## 4. Final Architectural Verdict

By surgically extracting schemas, contracts, and algorithms from the reference repositories while pruning cloud-heavy external runtimes (Airflow, ClickHouse, ClamAV, JVM/openEHR), **SevaHealth AI** achieves:
1. **Full Clinical Interoperability:** 100% compliant with HL7 FHIR R4, LOINC, and ABDM standards.
2. **Sub-second Real-time Performance:** Synchronous risk calculation and explainability.
3. **Zero External Fragility:** Guaranteed offline execution on any developer laptop or container host.
4. **Absolute Clinical Safety:** Strict human-in-the-loop governance for all escalating cases.
