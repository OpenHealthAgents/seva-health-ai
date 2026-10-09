# SevaHealth AI: District & State-Scale Scalability Architecture (PROMPT 28)

## 1. Executive Summary & Vision

To achieve the public health vision of the **Ayushman Bharat Digital Mission (ABDM)** and the **National Health Mission (NHM)**, SevaHealth AI is engineered from the ground up for massive horizontal scalability. The platform shifts healthcare from episodic illness management to continuous, population-wide preventive disease surveillance across **Talukas, Districts, and States**.

```
                   STATE-SCALE ARCHITECTURE TOPOLOGY
                   
  [65M+ Citizens / 10K+ PHCs / 50K+ ASHA Workers]
                         │
                         ▼ (HTTPS / mTLS / HTTP/2)
            ┌─────────────────────────┐
            │   Cloudflare Edge / CDN  │ (DDoS Guard, Rate Limiting, WAF)
            └────────────┬────────────┘
                         │
                         ▼
            ┌─────────────────────────┐
            │  L7 Ingress Controller   │ (Traefik / NGINX Envoy Gateway)
            └────────────┬────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────────┐ ┌───────────────┐ ┌─────────────────┐
│ API Gateway     │ │ API Gateway   │ │ API Gateway     │ (Horizontal Pod Autoscaling)
│ (Stateless Pod 1│ │(Stateless Pod │ │(Stateless Pod N)│
└────────┬────────┘ └───────┬───────┘ └────────┬────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
               ┌────────────┴────────────┐
               │  Event Mesh & Job Bus   │ (Redis Streams / Apache Kafka)
               └────────────┬────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Document OCR  │   │   Wearable    │   │  AI Clinical  │
│ Worker Pool   │   │ Telemetry Pod │   │  Worker Pool  │
└───────────────┘   └───────────────┘   └───────────────┘
```

---

## 2. Scalability Targets & Sizing Matrix

The platform specifies distinct operational tiers from local community pilot to nationwide deployment:

| Dimension / Metric | Pilot (100 Users) | Taluka (1,000 Users) | District (10,000 Users) | State Tier (100,000 Users) | State Full Scale (1,000,000+) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Active Citizens** | 100 | 1,000 | 10,000 | 100,000 | 1,000,000+ |
| **Concurrent Requests** | 10 req/s | 50 req/s | 500 req/s | 2,500 req/s | 15,000 req/s |
| **API Latency (p95)** | $< 25\text{ms}$ | $< 40\text{ms}$ | $< 65\text{ms}$ | $< 95\text{ms}$ | $< 120\text{ms}$ |
| **Risk Calculation (p95)** | $< 1\text{ms}$ | $< 2\text{ms}$ | $< 3\text{ms}$ | $< 5\text{ms}$ | $< 8\text{ms}$ |
| **Risk Throughput** | 1,000 evals/s | 5,000 evals/s | 12,000 evals/s | 25,000 evals/s | 50,000+ evals/s |
| **AI Response Latency** | $< 500\text{ms}$ | $< 800\text{ms}$ | $< 1.2\text{s}$ | $< 1.5\text{s}$ | Async Queued |
| **DB Ingestion (writes/s)**| 200 ops/s | 1,500 ops/s | 8,000 ops/s | 25,000 ops/s | 100,000+ ops/s |
| **Wearable Throughput** | 5,000 pts/s | 25,000 pts/s | 100,000 pts/s | 500,000 pts/s | 2,000,000+ pts/s |
| **Document OCR Queue** | Synchronous | Async ($\le 2\text{s}$) | Async ($\le 3\text{s}$) | Async ($\le 5\text{s}$) | Distributed OCR Nodes |
| **Notification Velocity** | 50 msgs/s | 250 msgs/s | 1,200 msgs/s | 5,000 msgs/s | 25,000 msgs/s |

---

## 3. Core Architectural Principles: Zero-Blocking Citizen UX

High-scale healthcare systems must never degrade interactive citizen experiences due to expensive computational jobs. SevaHealth AI enforces strict **Asynchronous Decoupling**:

### 3.1 Non-Blocking Operations
1. **Document OCR & Entity Extraction:**
   - When a citizen or ASHA worker uploads a multi-page lab slip or discharge summary, the API performs cryptographic hash validation, sanitizes the filename, enqueues the job to `QueueType.DOCUMENT_OCR`, and returns **HTTP 202 Accepted** in $< 30\text{ms}$.
   - Heavy image preprocessing, OCR contrast enhancement, and NER entity mapping execute asynchronously across background worker pools. The mobile UI displays an animated processing badge and receives a webhook/polling event when ready.
2. **Wearable Timeseries Backfill:**
   - Connecting Garmin, Apple Health, or Google Health Connect can synchronize 90 to 365 days of minute-by-minute biometric timeseries ($> 500,000$ points).
   - The endpoint `/wearables/backfill-async/{citizen_id}` ingests the bulk payload into `QueueType.WEARABLE_BACKFILL` in $< 20\text{ms}$, while TimescaleDB / ClickHouse hypertable partitions stream chunks in the background.
3. **Long Multi-Agent AI Workflows:**
   - Complex multi-agent consensus (ScreeningAgent $\rightarrow$ RiskAssessmentAgent $\rightarrow$ TrendAnalysisAgent $\rightarrow$ PreventionAgent $\rightarrow$ EscalationAgent) or SOAP note synthesis is processed via `QueueType.AI_WORKFLOW`.
4. **Population Epidemiological Analytics:**
   - Generating state-wide cohort microdata exports ($n = 50,000+$) with $k$-anonymity suppression ($k \ge 10$) is routed to `QueueType.POPULATION_ANALYTICS`. The public health admin receives a download ticket immediately.
5. **Multi-Channel Notification Broadcasts:**
   - Pushing 100,000 morning medication/walk reminders or flood/heatwave health warnings is queued into `QueueType.NOTIFICATION_DISPATCH` and broadcast through asynchronous telecom worker workers.

---

## 4. Database Sharding & Partitioning Strategy

### 4.1 Multi-Tenant Sharding by District
- In India's public health hierarchy, administration is partitioned by **State $\rightarrow$ District $\rightarrow$ Taluka $\rightarrow$ Primary Health Centre (PHC) $\rightarrow$ Sub-Centre / Ward**.
- SevaHealth AI partitions storage using a composite sharding key:
  $$\text{ShardKey} = \text{tenant\_id} + \text{district\_id} + \text{hash}(\text{ABHA\_ID}) \pmod N$$
- This guarantees:
  1. District medical officers query only their local district partition.
  2. Citizens' medical records reside deterministically on predictable database nodes.
  3. No cross-district table scanning during routine citizen check-ins.

### 4.2 Separation of Relational & Timeseries Stores
- **PostgreSQL / CockroachDB (Relational Core):** Citizen identity, ABHA registry, Consent Directives, RBAC credentials, Care Plans, Clinical Triage Queue cases.
- **TimescaleDB / ClickHouse (Biometric Telemetry):** Wearable heart rate timeseries, continuous glucose monitoring (CGM), step telemetry, SpO2 records. Uses automatic compression (10:1 ratio) and chunk partition dropping after 365 days.
- **Redis Cluster (In-Memory Hot Layer):** JWT session blacklist/tokens, active rate limit sliding windows, high-priority emergency triage alert buffers, and PriorityQueue backplanes.

---

## 5. Distributed Resilience & Circuit Breaking

- **Rate Limiting:** Sliding-window token bucket enforced at the edge (`120 req/min` for citizens, `600 req/min` for health worker screening camps).
- **Graceful Degradation:** If external LLM providers experience elevated latency or outages, the AI agent layer instantly falls back to deterministic rule-based explainability engines (`FailureBehavior.FALLBACK_TO_DETERMINISTIC`) without dropping requests.
- **Dead-Letter Queue (DLQ):** Failed asynchronous jobs retry 3 times with exponential backoff (`initial_delay = 200ms`, `factor = 2.0`). Poison pills are diverted to `DLQ` for clinical engineer inspection.
