# SevaHealth AI — Enterprise Production Deployment & Disaster Recovery Guide

> **Operational Standards**: ABDM (Ayushman Bharat Digital Mission), FHIR R4, openEHR Archetypes, DISHA Healthcare Data Privacy, Open Wearables Production Guidelines  
> **Image Policy**: 100% Pinned Stable Releases — Zero Nightly, Floating, or Unpinned Images.

---

## 1. Architecture Topology & Component Overview

SevaHealth AI is deployed as a resilient, modular, twelve-component microservice topology orchestrated via Docker Compose:

```
                            [ Internet / Public Network ]
                                          │
                                          ▼
                ┌──────────────────────────────────────────────────┐
                │        Component 12: NGINX Reverse Proxy        │
                │        (nginx:1.27.0-alpine - Pinned)            │
                │  - TLS Termination & HSTS                        │
                │  - Rate Limiting Zones (API & Auth)              │
                │  - Unified Path Routing & Gzip Compression       │
                └───────┬──────────────┬──────────────┬────────────┘
                        │              │              │
        ┌───────────────┘              │              └───────────────┐
        │ /api, /docs, web apps        │ /api/v1/ai-service           │ /grafana
        ▼                              ▼                              ▼
┌────────────────────────┐   ┌────────────────────┐   ┌────────────────────────┐
│  Component 1: API      │   │ Component 10: AI   │   │ Component 11:          │
│  Gateway & Core        │   │ Decision Service   │   │ Observability Portal   │
│  (sevahealth-api)      │   │ (sevahealth-ai)    │   │ (Prometheus & Grafana) │
│  - FastAPI Engine      │   │ - Multi-Agent Plan │   │ - prom/prometheus:     │
│  - FHIR R4 & ABDM      │   │ - Trajectory LLM   │   │   v2.52.0              │
│  - Auth & RBAC         │   │ - Clinical Copilot │   │ - grafana/grafana:     │
└───────┬────────┬───────┘   └─────────┬──────────┘   │   11.0.0               │
        │        │                     │              └────────────────────────┘
        │        │                     │
        │        └──────────────┐      │
        ▼                       ▼      ▼
┌────────────────────────┐   ┌────────────────────────────────┐
│ Component 2 & 3: Web   │   │ Component 5: Redis Cache & Bus │
│ Apps & Mobile Gateway  │   │ (redis:7.2.5-alpine - Pinned)  │
│ - Health Worker Web    │   │ - Priority Queue Transport     │
│ - Clinician Copilot    │   │ - Hot Cache & Token Blacklist  │
│ - Citizen Mobile Web   │   └───────┬────────────────────────┘
│ - Public Health Intel  │           │
└────────────────────────┘           ▼
                             ┌────────────────────────────────┐
                             │ Component 8: Async Worker Pool │
                             │ (sevahealth-worker)            │
                             │ - Document OCR & Parsing       │
                             │ - Wearable Timeseries Ingest   │
                             │ - State Population Analytics   │
                             │ - High-Throughput Notification │
                             └────────────────────────────────┘
                                     │
                                     ▼
                             ┌────────────────────────────────┐
                             │ Component 9: Periodic Scheduler│
                             │ (sevahealth-scheduler)         │
                             │ - Daily Habit Reminders        │
                             │ - Nocturnal Risk Surveillance  │
                             │ - Weekly Public Health Rollup  │
                             └────────────────────────────────┘

        ═════════════════════ DATA STORAGE TIER ═════════════════════

┌────────────────────────┐   ┌────────────────────┐   ┌────────────────────────┐
│ Component 4: Primary   │   │ Component 7: S3    │   │ Component 6: openEHR   │
│ Clinical PostgreSQL    │   │ Vault (MinIO)      │   │ Longitudinal Storage   │
│ (postgres:16.3-alpine) │   │ (RELEASE.2024-05)  │   │ (ehrbase:2.15.0 &      │
│ - Longitudinal Records │   │ - Encrypted PDFs   │   │  ehrdb:16.3-alpine)    │
│ - Relational Store     │   │ - Medical Scans    │   │ - Standardized EHR     │
│ - Schema Migrations    │   │ - Model Artifacts  │   │ - Archetype Repository │
└────────────────────────┘   └────────────────────┘   └────────────────────────┘
```

---

## 2. Pinned Image & Dependency Specification

In accordance with Open Wearables and clinical deployment standards, **never use `:latest`, `:next`, or nightly branch builds in production**. All dependencies are frozen:

| Component | Pinned Version / Tag | Verification SHA / Protocol |
|:---|:---|:---|
| **API & Python Runtimes** | `python:3.12-slim` | Debian Bookworm Minimal |
| **Primary Clinical DB** | `postgres:16.3-alpine` | Alpine 3.20 Linux |
| **openEHR DB (ehrdb)** | `postgres:16.3-alpine` | Dedicated isolated persistence |
| **openEHR EHRbase** | `ehrbase/ehrbase:2.15.0` | Official openEHR stable release |
| **Redis Broker** | `redis:7.2.5-alpine` | In-memory queue & token store |
| **Object Storage Vault** | `minio/minio:RELEASE.2024-05-10T01-41-38Z` | Stable S3-compatible build |
| **Reverse Proxy** | `nginx:1.27.0-alpine` | TLS 1.3 / OWASP hardened |
| **Metrics Scraper** | `prom/prometheus:v2.52.0` | Production telemetry collector |
| **Telemetry Dashboard** | `grafana/grafana:11.0.0` | Pre-provisioned dashboards |
| **Python Dependencies** | `requirements-prod.txt` | Complete strict lockfile |

---

## 3. Local Development Setup

For rapid local iteration, SevaHealth provides live code hot-reloading:

### Prerequisites
- Docker Engine 24.0+ & Docker Compose v2.20+
- Python 3.11+ (or 3.12 recommended)
- 4 GB Available RAM

### Launch Commands
```bash
# 1. Clone repository and enter directory
cd /path/to/seva-health-ai

# 2. Copy development environment file
cp .env.example .env

# 3. Launch development stack
docker compose -f docker-compose.dev.yml up -d

# 4. View real-time logs
docker compose -f docker-compose.dev.yml logs -f sevahealth-api-dev
```

### Local Access Points
- **API Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Probe**: [http://localhost:8000/health](http://localhost:8000/health)
- **Health Worker Portal**: [http://localhost:8000/health-worker-app](http://localhost:8000/health-worker-app)
- **Clinician Copilot**: [http://localhost:8000/clinician-app](http://localhost:8000/clinician-app)
- **Citizen Mobile Web**: [http://localhost:8000/citizen-app](http://localhost:8000/citizen-app)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`)

---

## 4. Evaluation Demo Mode Setup

For judges, evaluators, and challenge demonstrations, Demo Mode initializes all 10 synthetic clinical personas, wearable timeseries, risk trajectories, and population metrics in **under 2 minutes**:

```bash
# 1. Launch pre-seeded demo stack
docker compose -f docker-compose.demo.yml up -d

# 2. Execute end-to-end 16-step challenge demonstration workflow
docker exec -it sevahealth-demo-api python scripts/run_challenge_demo.py

# 3. Access unified frontend demo
# Point browser to http://localhost (Port 80 routed through NGINX)
```

### Reset Demo Environment
To return the demo stack to a pristine seed state at any time:
```bash
docker exec -it sevahealth-demo-api python scripts/seed_data.py --reset
```

---

## 5. Staging Environment Deployment

Staging mirrors production with synthetic cohort validation and ABDM sandbox connectors:

1. **Environment Configuration**:
   ```bash
   cp .env.example .env.staging
   # Set ENVIRONMENT=staging
   # Set LOG_LEVEL=DEBUG
   # Configure ABDM sandbox API credentials
   ```
2. **Apply Database Migrations**:
   ```bash
   python scripts/migrate.py --status
   python scripts/migrate.py
   ```
3. **Execute Pre-flight Smoke Tests**:
   ```bash
   python scripts/ci_gates.py
   ```

---

## 6. Production Deployment Hardening

### Pre-Deployment Checklist
- [x] All container images strictly pinned (no `:latest` or `:next`).
- [x] Containers run as non-root application user `seva:seva`.
- [x] Mandatory health checks configured on all 12 services with start periods and retries.
- [x] Resource quotas (`cpus` and `memory` limits) declared in `deploy.resources.limits`.
- [x] Network boundary isolation enabled via Docker bridge networks.
- [x] Persistent volumes mapped for PostgreSQL, Redis, MinIO, openEHR, Prometheus, and Grafana.

### Starting the Production Stack
```bash
# 1. Populate production secrets
cp .env.example .env
chmod 600 .env
# Edit .env: update SECRET_KEY, POSTGRES_PASSWORD, EHRBASE_PASSWORD, etc.

# 2. Run pending database migrations
python scripts/migrate.py

# 3. Launch all production services
docker compose -f docker-compose.yml up -d --build

# 4. Verify healthy state of all 12 containers
docker compose -f docker-compose.yml ps
```

Expected output:
```
NAME                         IMAGE                                        STATUS
sevahealth-reverse-proxy     nginx:1.27.0-alpine                          healthy
sevahealth-api               sevahealth-ai-sevahealth-api                 healthy
sevahealth-worker            sevahealth-ai-sevahealth-worker              healthy
sevahealth-scheduler         sevahealth-ai-sevahealth-scheduler           healthy
sevahealth-ai                sevahealth-ai-sevahealth-ai                  healthy
sevahealth-postgres          postgres:16.3-alpine                         healthy
sevahealth-redis             redis:7.2.5-alpine                           healthy
sevahealth-minio             minio/minio:RELEASE.2024-05-10T01-41-38Z    healthy
sevahealth-ehrdb             postgres:16.3-alpine                         healthy
sevahealth-ehrbase           ehrbase/ehrbase:2.15.0                       healthy
sevahealth-prometheus        prom/prometheus:v2.52.0                      healthy
sevahealth-grafana           grafana/grafana:11.0.0                       healthy
```

---

## 7. Database Migration Strategy

SevaHealth AI implements a transactional, ledger-tracked migration strategy:

### Migration Architecture
- Directory: `infrastructure/postgres/migrations/`
- Schema Ledger Table: `schema_migrations`
- Cryptographic Integrity: Every migration script is hashed via SHA-256 to detect tampering.

### Running Migrations
```bash
# Check status of applied vs pending migrations
python scripts/migrate.py --status

# Dry-run validation
python scripts/migrate.py --check

# Apply all pending migrations sequentially inside transactions
python scripts/migrate.py
```

### Writing New Migrations
1. Name new migrations with zero-padded sequences: `002_add_cardiac_telemetry.sql`.
2. Ensure idempotent statements (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`).
3. Commit migration script into git repository.

---

## 8. Database Backup Strategy

To guarantee zero clinical data loss and maintain ISO/DISHA compliance, automated point-in-time logical backups are scheduled:

### Key Features
- **Gzip Compression**: Compresses standard dumps by ~85% into `.sql.gz`.
- **SHA-256 Checksum**: Generates `.sha256` digest for cryptographic validation.
- **JSON Manifest**: Logs timestamp, size, database version, and verification status.
- **Retention Policy**: Automatically cleans up backups older than 30 days.

### Executing a Backup
```bash
# Automated Python runner
python scripts/backup_database.py --output-dir /var/backups/sevahealth --retention-days 30

# Or via bash wrapper
./scripts/backup_database.sh
```

### Backup Artifact Structure
```
/var/backups/sevahealth/
├── sevahealth_backup_20261009_140000.sql.gz
├── sevahealth_backup_20261009_140000.sha256
└── sevahealth_backup_20261009_140000.manifest.json
```

### Automated Cron Job (Production Host)
Add the following line to `/etc/crontab` to trigger hourly backups:
```cron
0 * * * * root /app/scripts/backup_database.sh >> /var/log/sevahealth_backup.log 2>&1
```

---

## 9. Disaster Recovery & Restoration Procedures

In the event of hardware failure, catastrophic data corruption, or datacenter failover, follow this recovery protocol:

### Recovery Metrics Targets
- **Recovery Time Objective (RTO)**: `< 15 Minutes`
- **Recovery Point Objective (RPO)**: `< 1 Hour`

### Step-by-Step Recovery Procedure

#### Step 1: Quarantine & Pre-flight Inspection
Inspect backup archive integrity before touching the database:
```bash
python scripts/restore_database.py /var/backups/sevahealth/sevahealth_backup_20261009_140000.sql.gz --check
```

#### Step 2: Stop Incoming Traffic
Temporarily scale down the API Gateway to prevent write conflicts during restoration:
```bash
docker compose -f docker-compose.yml stop sevahealth-api sevahealth-worker sevahealth-scheduler
```

#### Step 3: Execute Database Restoration
```bash
python scripts/restore_database.py /var/backups/sevahealth/sevahealth_backup_20261009_140000.sql.gz --force
```

#### Step 4: Validate Data Integrity
Run database verification queries:
```bash
docker exec -it sevahealth-postgres psql -U seva -d sevahealth_db -c "SELECT count(*) FROM patients;"
docker exec -it sevahealth-postgres psql -U seva -d sevahealth_db -c "SELECT count(*) FROM screenings;"
```

#### Step 5: Restart Application Services & Unquarantine
```bash
docker compose -f docker-compose.yml start sevahealth-api sevahealth-worker sevahealth-scheduler
curl -f http://localhost:8000/health
```

---

## 10. Summary Checklist for Operations

| Action | Frequency | Responsible Tool |
|:---|:---|:---|
| **Health Monitoring** | Real-time (10s probes) | NGINX, Docker Healthcheck, Prometheus |
| **Log Inspection** | Continuous | Structlog with `X-Correlation-ID` |
| **Database Migrations** | On Release | `scripts/migrate.py` |
| **Point-in-Time Backups** | Hourly / Daily | `scripts/backup_database.py` |
| **Disaster Recovery Drill**| Quarterly | `scripts/restore_database.py` |
| **Security Audit** | Per sprint | `scripts/ci_gates.py` |
