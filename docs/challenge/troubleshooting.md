# SevaHealth AI — Challenge Troubleshooting Guide

> **Quick Health Probe**: `curl -f http://localhost:8000/health`  
> **Instant Demo Reset**: `python scripts/run_challenge_demo.py --reset`

---

## 1. Common Evaluator Questions & Solutions

### Issue 1: "Port 8000 (or Port 80) is already in use by another application"
- **Cause**: Another local web server or prior container is binding to port 8000.
- **Solution**:
  ```bash
  # Check which process is occupying port 8000 (Windows PowerShell):
  Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess
  
  # Or start SevaHealth on an alternate port:
  python -m uvicorn services.api.main:app --port 8080 --host 0.0.0.0
  ```

### Issue 2: "Docker daemon is not running on my machine"
- **Solution**: SevaHealth AI includes a **zero-dependency local execution mode**! You do not require Docker to evaluate the platform. Simply run:
  ```bash
  python scripts/demo.py
  python -m uvicorn services.api.main:app --reload --port 8000
  ```
  The platform will automatically fall back to local in-memory SQLite and mock AI provider mode.

### Issue 3: "The demo citizen state looks modified or already reviewed"
- **Cause**: A previous evaluation run progressed the citizen through the workflow.
- **Solution**: Trigger the instant **Demo Reset Button**:
  ```bash
  python scripts/run_challenge_demo.py --reset
  ```
  This immediately purges ephemeral challenge steps, restores Devendra Sharma to Month 0 baseline, and re-seeds all 12 clinical personas.

### Issue 4: "PostgreSQL driver error: No module named 'psycopg'"
- **Cause**: Python environment is running with local SQLite configuration.
- **Solution**: In `.env`, ensure `DATABASE_URL=sqlite:///./sevahealth.db` for local zero-dependency evaluation, or install `pip install psycopg[binary]` if evaluating against external PostgreSQL.

---

## 2. System Diagnostic Command Suite

```bash
# 1. Run Complete CI Quality Gates (Lint, Types, Unit, E2E, Security)
python scripts/ci_gates.py

# 2. Run Deployment Configuration Verification Tests
pytest tests/test_deployment_config.py -v

# 3. Inspect Live Telemetry Buffer
curl http://localhost:8000/metrics

# 4. View Migration Status Table
python scripts/migrate.py --status
```
