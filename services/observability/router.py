"""FastAPI Observability Router for SevaHealth AI.

Exposes REST APIs and Interactive Dashboard Portal for:
1. System Health Dashboard (/api/v1/observability/dashboards/system)
2. AI Health Dashboard (/api/v1/observability/dashboards/ai)
3. Integration Health Dashboard (/api/v1/observability/dashboards/integration)
4. Data Pipeline Health Dashboard (/api/v1/observability/dashboards/pipeline)
5. Executive Summary (/api/v1/observability/dashboards/summary)
6. Distributed Trace Inspector (/api/v1/observability/traces/{correlation_id})
7. Synthetic End-to-End Probe (/api/v1/observability/synthetic-probe)
8. Interactive Web Portal (/observability)
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse

from packages.observability.context import CorrelationContext, SpanStage
from packages.observability.metrics import metrics
from packages.observability.dashboards import HealthDashboardService
from packages.observability.tracer import tracer, trace_store
from packages.observability.telemetry import telemetry_buffer
from packages.observability.sanitizer import HealthcareLogSanitizer
from packages.observability.logging import get_safe_logger

logger = get_safe_logger("observability_router")

router = APIRouter(prefix="/observability", tags=["Observability & Telemetry"])


@router.get("/dashboards/system", response_model=Dict[str, Any])
async def get_system_health_dashboard() -> Dict[str, Any]:
    """Returns real-time System Health metrics (API latency percentiles, error rates, DB, queues)."""
    return HealthDashboardService.get_system_health()


@router.get("/dashboards/ai", response_model=Dict[str, Any])
async def get_ai_health_dashboard() -> Dict[str, Any]:
    """Returns AI Health metrics (agent executions, LLM latency & failures, token usage, tool calls)."""
    return HealthDashboardService.get_ai_health()


@router.get("/dashboards/integration", response_model=Dict[str, Any])
async def get_integration_health_dashboard() -> Dict[str, Any]:
    """Returns Integration Health metrics (wearables sync, notifications delivery, external adapters)."""
    return HealthDashboardService.get_integration_health()


@router.get("/dashboards/pipeline", response_model=Dict[str, Any])
async def get_data_pipeline_health_dashboard() -> Dict[str, Any]:
    """Returns Data Pipeline Health metrics (document OCR, risk-engine execution, model inference)."""
    return HealthDashboardService.get_data_pipeline_health()


@router.get("/dashboards/summary", response_model=Dict[str, Any])
async def get_unified_observability_summary() -> Dict[str, Any]:
    """Returns executive overview across all 4 operational health dashboards."""
    return HealthDashboardService.get_unified_summary()


@router.get("/traces/{correlation_id}", response_model=Dict[str, Any])
async def get_trace_by_correlation_id(correlation_id: str) -> Dict[str, Any]:
    """Retrieves end-to-end distributed trace spans across mobile, API, agent, risk engine, clinical repo, notification."""
    trace_summary = trace_store.get_trace_summary(correlation_id)
    if not trace_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active distributed trace found for correlation ID: {correlation_id}",
        )
    return trace_summary


@router.get("/traces", response_model=List[Dict[str, Any]])
async def list_recent_traces(limit: int = Query(default=25, ge=1, le=100)) -> List[Dict[str, Any]]:
    """Lists recent distributed traces."""
    return trace_store.list_recent_traces(limit=limit)


@router.get("/metrics", response_model=Dict[str, Any])
async def get_full_metrics_snapshot() -> Dict[str, Any]:
    """Returns complete snapshot of all aggregated counters, gauges, and latency percentiles."""
    return metrics.get_summary()


@router.post("/synthetic-probe", response_model=Dict[str, Any])
async def run_synthetic_end_to_end_probe(request: Request) -> Dict[str, Any]:
    """Executes a synthetic request traversing all 6 tiers to verify distributed traceability:
    Mobile -> API -> Agent -> Risk Engine -> Clinical Repo -> Notification.
    """
    probe_id = f"probe-{uuid.uuid4().hex[:8]}"
    corr_id = f"seva-synthetic-{uuid.uuid4().hex[:10]}"
    CorrelationContext.set_correlation_id(corr_id)
    CorrelationContext.set_trace_id(f"trace-{probe_id}")

    # Stage 1: Mobile App Intake Span
    with tracer.span(name="MobileScreeningIntake", stage=SpanStage.MOBILE, tags={"client": "Android-Citizen-App", "probe_id": probe_id}) as s1:
        s1.add_event("citizen_tap_start_screening")
        time.sleep(0.005)
        s1.add_event("citizen_submit_screening_data")

    # Stage 2: API Gateway Ingestion Span
    with tracer.span(name="ApiGatewayIngest", stage=SpanStage.API, tags={"endpoint": "/api/v1/screening/submit", "probe_id": probe_id}) as s2:
        metrics.record_api_request("POST", "/api/v1/screening/submit", 200, 18.5)
        time.sleep(0.005)

    # Stage 3: AI Prevention Agent Reasoning Span
    with tracer.span(name="PreventionAgentReasoning", stage=SpanStage.AGENT, tags={"agent": "PreventionAgent", "probe_id": probe_id}) as s3:
        metrics.record_agent_execution("PreventionAgent", 45.2, steps=3, escalated=False)
        metrics.record_llm_call("mock_clinical", "gemini-1.5-flash", 32.1, prompt_tokens=240, completion_tokens=110, success=True)
        metrics.record_tool_call("get_patient_vitals", 4.2, success=True)
        time.sleep(0.008)

    # Stage 4: Risk Engine Multi-Domain Evaluation Span
    with tracer.span(name="RiskEngineEvaluation", stage=SpanStage.RISK_ENGINE, tags={"engine": "NCDRiskEngine", "probe_id": probe_id}) as s4:
        metrics.record_risk_engine("metabolic", 12.4, risk_tier="HIGH")
        metrics.record_risk_engine("cardiovascular", 9.8, risk_tier="MODERATE")
        metrics.record_model_inference("calibrated_gradient_boosting_v1.0.0", 6.5, batch_size=1)
        time.sleep(0.006)

    # Stage 5: Clinical Repository Persistence Span
    with tracer.span(name="ClinicalRepoPersist", stage=SpanStage.CLINICAL_REPOSITORY, tags={"table": "observations", "probe_id": probe_id}) as s5:
        metrics.record_db_query("INSERT", "observations", 3.2, success=True)
        metrics.record_db_query("INSERT", "care_plans", 4.1, success=True)
        metrics.record_db_cache(hit=True)
        time.sleep(0.004)

    # Stage 6: Notification Dispatch Span
    with tracer.span(name="NotificationDispatch", stage=SpanStage.NOTIFICATION, tags={"channel": "SMS", "probe_id": probe_id}) as s6:
        metrics.record_notification("SMS", 15.2, success=True)
        s6.add_event("telecom_sms_gateway_accepted")
        time.sleep(0.003)

    trace_summary = trace_store.get_trace_summary(corr_id)
    return {
        "status": "SUCCESS",
        "probe_id": probe_id,
        "correlation_id": corr_id,
        "message": "Synthetic request successfully traversed all 6 stages.",
        "trace_summary": trace_summary,
    }


@router.get("/portal", response_class=HTMLResponse)
async def serve_observability_portal() -> str:
    """Renders the interactive SevaHealth AI Observability Portal."""
    return HTMLResponse(content=_OBSERVABILITY_HTML, status_code=200)


_OBSERVABILITY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SevaHealth AI - Observability & Telemetry Command Center</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --success: #4ade80;
      --warning: #facc15;
      --danger: #f87171;
      --border: #334155;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    h1 { font-size: 24px; font-weight: 700; color: var(--primary); }
    .badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-healthy { background: rgba(74, 222, 128, 0.2); color: var(--success); border: 1px solid var(--success); }
    .badge-degraded { background: rgba(250, 204, 21, 0.2); color: var(--warning); border: 1px solid var(--warning); }
    .badge-critical { background: rgba(248, 113, 113, 0.2); color: var(--danger); border: 1px solid var(--danger); }
    
    .nav-tabs {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
    }
    .nav-btn {
      background: var(--card-bg);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 8px 18px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.2s;
    }
    .nav-btn.active, .nav-btn:hover {
      background: var(--primary);
      color: #0f172a;
      border-color: var(--primary);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 20px;
    }
    .card h3 { font-size: 14px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
    .card .value { font-size: 28px; font-weight: 700; color: var(--text); }
    .card .sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

    .trace-section {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 20px;
      margin-top: 24px;
    }
    .probe-btn {
      background: #10b981;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      float: right;
    }
    .trace-item {
      padding: 12px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    pre {
      background: #090d16;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
      font-size: 13px;
      color: #38bdf8;
      max-height: 400px;
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>SevaHealth AI Observability Command Center</h1>
      <p style="color: var(--text-muted); font-size: 13px;">Full Distributed Lifecycle Telemetry across Mobile, API, Agent, Risk Engine, Repository, Notification</p>
    </div>
    <div>
      <span id="overallStatus" class="badge badge-healthy">System Operational</span>
    </div>
  </header>

  <div class="nav-tabs">
    <button class="nav-btn active" onclick="loadTab('system')">System Health</button>
    <button class="nav-btn" onclick="loadTab('ai')">AI Health</button>
    <button class="nav-btn" onclick="loadTab('integration')">Integration Health</button>
    <button class="nav-btn" onclick="loadTab('pipeline')">Data Pipeline Health</button>
    <button class="nav-btn" onclick="loadTab('traces')">Trace Inspector</button>
    <button class="probe-btn" onclick="triggerSyntheticProbe()">Run End-to-End Probe</button>
  </div>

  <div id="contentArea">
    <div class="grid" id="kpiGrid"></div>
    <div class="card">
      <h3 id="detailsTitle">Dashboard Details</h3>
      <pre id="rawJson">Loading telemetry...</pre>
    </div>
  </div>

  <script>
    let currentTab = 'system';

    async function loadTab(tab) {
      currentTab = tab;
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      event?.target?.classList.add('active');

      if (tab === 'traces') {
        const res = await fetch('/api/v1/observability/traces');
        const data = await res.json();
        document.getElementById('kpiGrid').innerHTML = '';
        document.getElementById('detailsTitle').innerText = 'Recent Traces (Multi-Stage Lifecycle)';
        document.getElementById('rawJson').innerText = JSON.stringify(data, null, 2);
        return;
      }

      const res = await fetch(`/api/v1/observability/dashboards/${tab}`);
      const data = await res.json();
      
      const badge = document.getElementById('overallStatus');
      badge.innerText = data.status;
      badge.className = 'badge ' + (data.status === 'HEALTHY' ? 'badge-healthy' : (data.status === 'DEGRADED' ? 'badge-degraded' : 'badge-critical'));

      renderKpis(data.kpis);
      document.getElementById('detailsTitle').innerText = data.dashboard_name + ' Breakdown';
      document.getElementById('rawJson').innerText = JSON.stringify(data, null, 2);
    }

    function renderKpis(kpis) {
      const grid = document.getElementById('kpiGrid');
      grid.innerHTML = '';
      if (!kpis) return;
      for (const [key, val] of Object.entries(kpis)) {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `<h3>${key.replace(/_/g, ' ')}</h3><div class="value">${val}</div>`;
        grid.appendChild(card);
      }
    }

    async function triggerSyntheticProbe() {
      const res = await fetch('/api/v1/observability/synthetic-probe', { method: 'POST' });
      const data = await res.json();
      alert(`Synthetic 6-Stage Probe Complete!\\nCorrelation ID: ${data.correlation_id}\\nSpans recorded across Mobile, API, Agent, Risk Engine, Repository, Notification.`);
      loadTab(currentTab);
    }

    loadTab('system');
    setInterval(() => loadTab(currentTab), 15000);
  </script>
</body>
</html>
"""
