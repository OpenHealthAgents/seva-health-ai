# SevaHealth AI — Repository Reuse & Attribution Architecture

> **Strategic Architecture**: Turning existing open-source and health infrastructure into foundational components of a single, coherent product.

---

## 1. Strategic Repository Reuse Priority Map

SevaHealth AI leverages established, hardened open-source repositories as infrastructure building blocks, avoiding the pitfall of reinventing foundational plumbing and focusing its engineering on the core innovation: **NCD Risk Trajectories & Decision Intelligence**.

| Repository | SevaHealth Architectural Role | Concrete Implementation in Codebase |
|:---|:---|:---|
| **bezs-iam** | Identity, Authentication & Role-Based Access Control (RBAC) | [`packages/auth/jwt.py`](file:///d:/seva-health-ai/packages/auth/jwt.py), [`services/identity/`](file:///d:/seva-health-ai/services/identity/). Multi-tenant JWT generation, password hashing, and role validation. |
| **bezs-filenest** | Secure Document & Medical File Storage | [`services/documents/`](file:///d:/seva-health-ai/services/documents/). Presigned MinIO S3 uploads, SHA-256 file verification, and MIME validation. |
| **bezs-pipeline** | Asynchronous Data & Document OCR Pipelines | [`packages/queue/`](file:///d:/seva-health-ai/packages/queue/), [`services/jobs/`](file:///d:/seva-health-ai/services/jobs/). Priority queue processing for document ingestion and OCR. |
| **Open Wearables** | Wearable Biometric Ingestion & Data Normalization | [`services/wearable/adapter.py`](file:///d:/seva-health-ai/services/wearable/adapter.py), [`services/wearable/projections.py`](file:///d:/seva-health-ai/services/wearable/projections.py). Self-hosted multi-provider normalization (Garmin, Fitbit, Apple Health) and rolling 7-day baselines. |
| **EHRbase** | openEHR Longitudinal Clinical Repository | [`packages/clinical_models/openehr_builder.py`](file:///d:/seva-health-ai/packages/clinical_models/openehr_builder.py). Canonical archetype composition generation and dual-write storage. |
| **bezs-observability** | Structured Logging, Distributed Tracing & Metrics | [`packages/observability/`](file:///d:/seva-health-ai/packages/observability/). Context propagation (`X-Correlation-ID`), zero-PHI sanitization, and Prometheus metrics. |
| **bezs-emr-gql** | EMR GraphQL Interoperability & Federation | [`services/clinical/emr_federation.py`](file:///d:/seva-health-ai/services/clinical/emr_federation.py). Federated GraphQL client with circuit breaker fallbacks. |
| **bezs-hms** | Hospital Management System Outpatient Workflow | [`services/clinical/hms_client.py`](file:///d:/seva-health-ai/services/clinical/hms_client.py). Referrals and triage scheduling integration with secondary/tertiary facilities. |
| **bezs-emr-mcp** | Controlled Clinical Data Model Context Protocol (MCP) | [`services/ai_agent/interop_tools.py`](file:///d:/seva-health-ai/services/ai_agent/interop_tools.py). Bounded tool calling with patient boundary isolation. |
| **DrGodly Mobile** | Mobile UI & Low-Literacy Health Application Patterns | [`apps/citizen-mobile/index.html`](file:///d:/seva-health-ai/apps/citizen-mobile/index.html). Visual trajectory cards, audio playback, and vernacular language toggles. |
| **refactoragent** | Multi-Agent Orchestration & Tool Calling Patterns | [`agents/`](file:///d:/seva-health-ai/agents/), [`services/ai_agent/prevention_agent.py`](file:///d:/seva-health-ai/services/ai_agent/prevention_agent.py). Bounded agent reasoning loops with strict safety verification. |

---

## 2. Why Open Wearables is Foundational

As noted in architectural evaluations, **Open Wearables** is uniquely suited for SevaHealth AI because:
1. **Self-Hostable**: Can be deployed on private state government cloud infrastructure without exporting sensitive citizen biometrics to foreign cloud services.
2. **Provider-Agnostic Normalization**: Ingests diverse formats (Apple HealthKit XML, Garmin Health API, Fitbit Web API) and standardizes them into canonical JSON timeseries.
3. **AI-Ready Baselines**: Computes rolling 7-day moving averages (resting heart rate, daily step velocity, deep sleep ratios) explicitly designed for machine learning feature vectors.

---

## 3. Coherent Product Integration (Not a Fragmented Collection)

Rather than presenting an unintegrated patchwork of projects, SevaHealth AI cleanly positions these repositories as **foundational infrastructure tiers** beneath a unified preventive health decision-intelligence engine. Every component communicates through strongly-typed contracts, unified correlation logging, and standardized clinical vocabularies (LOINC, SNOMED-CT, openEHR).
