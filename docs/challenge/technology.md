# SevaHealth AI — Technology Stack & Engineering Standards

> **Compliance**: Open Wearables Production Guidelines, ABDM Specifications, DISHA Privacy Rules  
> **Image & Dependency Policy**: Strictly Pinned Stable Versions — Zero Nightly or Floating Builds

---

## 1. Complete Technology Stack Matrix

| Tier / Domain | Selected Technology | Pinned Version | Rationale & Standards |
|:---|:---|:---|:---|
| **ASGI Application Engine** | FastAPI | `0.115.0` | Ultra-high throughput asynchronous Python web framework |
| **Web Server** | Uvicorn (standard) | `0.32.0` | Production ASGI HTTP server with uvloop event loop |
| **Data Validation & Typing** | Pydantic v2 | `2.9.2` | High-performance C-accelerated schema validation |
| **Relational Clinical Store** | PostgreSQL (Alpine) | `16.3-alpine` | ACID-compliant relational storage with JSONB support |
| **ORM & Database Driver** | SQLAlchemy / Psycopg 3 | `2.0.35` / `3.2.1` | Asynchronous connection pooling & dialect abstraction |
| **In-Memory Cache & Message Bus** | Redis | `7.2.5-alpine` | Priority queue broker & sub-millisecond token cache |
| **Longitudinal Clinical Repo** | EHRbase (openEHR) | `2.15.0` | Universal openEHR clinical archetype persistence |
| **Object Storage Medical Vault** | MinIO S3 | `RELEASE.2024-05-10` | S3-compatible encrypted medical document storage |
| **Wearable Telemetry Pipeline** | Open Wearables Layer | `1.0.0` (Pinned) | Multi-provider biometric ingestion & baseline normalization |
| **Reverse Proxy & Gateway** | NGINX | `1.27.0-alpine` | TLS 1.3 termination, OWASP security headers, gzip, rate limiting |
| **Metrics Collector** | Prometheus | `v2.52.0` | High-efficiency multi-dimensional time series scraper |
| **Real-time Observability** | Grafana | `11.0.0` | Auto-provisioned dashboards for system & AI telemetry |
| **Machine Learning Engine** | Scikit-learn / SciPy / NumPy | `1.5.2` / `1.13.1` / `1.26.4` | Isotonic calibrated probabilistic inference pipelines |
| **Security & Cryptography** | Python-Jose / Cryptography | `3.3.0` / `43.0.1` | HMAC-SHA256 JWT tokens & AES-256-GCM symmetric encryption |
| **Containerization Runtime** | Docker Engine & Compose | `24.0+` / `v2.20+` | Multi-container reproducible isolated topology |

---

## 2. Pinned Dependencies Discipline

In accordance with the **Open Wearables Production Guidelines**:
- Floating tags like `:latest`, `:next`, or Git branches like `main` are strictly forbidden in production.
- Every single image in `docker-compose.yml`, `docker-compose.dev.yml`, and `docker-compose.demo.yml` has an explicit semantic version tag.
- All Python packages are locked in `requirements-prod.txt` with exact `==` pins.

---

## 3. Engineering Quality Gates

The codebase enforces nine mandatory automated CI quality gates:
1. Static code analysis via Ruff (`ruff check .`)
2. Type checking via Mypy (`mypy packages services agents ml`)
3. Unit tests (100% pass)
4. Integration and FHIR contract validation
5. Security penetration tests (OWASP Top 10, IDOR, SQL injection, prompt injection)
6. Asynchronous queue non-blocking latency SLA (< 150 ms)
7. Scalability benchmarks across 100 to 100,000 synthetic records
8. Model card and calibration checks
9. Container configuration & pinned image linting
