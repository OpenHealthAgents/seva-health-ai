"""Comprehensive Test Suite for Observability & Distributed Telemetry (PROMPT 22).

Verifies:
1. Application logs, API latency, errors, DB metrics, queue metrics.
2. Agent execution, LLM latency, LLM failures, token usage, tool calls.
3. Risk-engine execution, model inference, wearable sync, document pipeline, notifications, audit events.
4. Strict Healthcare Data / PHI scrubbing in ordinary application logs.
5. Correlation IDs and distributed tracing across all 6 stages:
   mobile -> API -> agent -> risk engine -> clinical repository -> notification.
6. The 4 dedicated dashboards:
   - System Health
   - AI Health
   - Integration Health
   - Data Pipeline Health
"""

import time
import uuid
import pytest
from starlette.testclient import TestClient

from services.api.main import app
from packages.observability.context import CorrelationContext, SpanStage
from packages.observability.sanitizer import HealthcareLogSanitizer, SENSITIVE_CLINICAL_KEYS
from packages.observability.metrics import metrics, LatencyTracker
from packages.observability.tracer import tracer, trace_store
from packages.observability.dashboards import HealthDashboardService
from packages.observability.telemetry import telemetry_buffer
from packages.observability.audit import audit_logger
from packages.types.enums import AuditAction, UserRole

client = TestClient(app)


# ==============================================================================
# 1. Healthcare Data / PHI Redaction in Application Logs
# ==============================================================================

def test_healthcare_data_scrubbed_from_ordinary_logs():
    """Healthcare data must NOT be written into ordinary application logs unnecessarily."""
    raw_sensitive_payload = {
        "citizen_id": "citizen-ramesh-patel-01",
        "first_name": "Ramesh",
        "last_name": "Patel",
        "phone": "+91 98450 12345",
        "email": "ramesh@example.com",
        "abha_id": "91-4829-1029-4820",
        "systolic_bp": 142.0,
        "diastolic_bp": 92.0,
        "fasting_glucose": 126.0,
        "hba1c": 6.8,
        "serum_creatinine": 1.1,
        "diagnosis": "Essential Stage 1 Hypertension with Prediabetes",
        "medication": "Metformin 500mg daily",
        "safe_operational_key": "PROCESS_BATCH_01",
        "batch_status": "SUCCESS",
    }

    sanitized = HealthcareLogSanitizer.sanitize_data(raw_sensitive_payload)

    # Raw sensitive clinical values must be redacted
    assert sanitized["systolic_bp"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER
    assert sanitized["diastolic_bp"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER
    assert sanitized["fasting_glucose"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER
    assert sanitized["hba1c"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER
    assert sanitized["serum_creatinine"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER
    assert sanitized["diagnosis"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER
    assert sanitized["medication"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER
    assert sanitized["first_name"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER
    assert sanitized["phone"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER
    assert sanitized["abha_id"] == HealthcareLogSanitizer.REDACTED_PLACEHOLDER

    # Citizen ID is masked for privacy while retaining trace context
    assert "..." in sanitized["citizen_id"] or "***" in sanitized["citizen_id"]
    assert sanitized["citizen_id"] != "citizen-ramesh-patel-01"

    # Non-clinical operational metadata must be preserved
    assert sanitized["safe_operational_key"] == "PROCESS_BATCH_01"
    assert sanitized["batch_status"] == "SUCCESS"


def test_free_text_phi_redaction():
    """String scanner detects and redacts phone numbers, emails, ABHA IDs, and blood pressure strings."""
    free_text = (
        "Patient Ramesh Patel, phone +91 98450 12345, ABHA 91-4829-1029-4820, "
        "reported blood pressure 150/95 mmHg and sugar 180 mg/dL to doctor@sevahealth.ai."
    )
    clean_text = HealthcareLogSanitizer.sanitize_string(free_text)

    assert "+91 98450 12345" not in clean_text
    assert "[REDACTED_PHONE]" in clean_text
    assert "91-4829-1029-4820" not in clean_text
    assert "[REDACTED_ABHA]" in clean_text
    assert "doctor@sevahealth.ai" not in clean_text
    assert "[REDACTED_EMAIL]" in clean_text
    assert "150/95 mmHg" not in clean_text
    assert "[REDACTED_BP]" in clean_text
    assert "180 mg/dL" not in clean_text
    assert "[REDACTED_GLUCOSE]" in clean_text


# ==============================================================================
# 2. Correlation ID & Distributed Tracing
# ==============================================================================

def test_correlation_id_propagated_in_api_response():
    """Every HTTP request must preserve or generate a traceable correlation ID in response headers."""
    client_corr_id = f"mobile-client-{uuid.uuid4().hex[:8]}"

    # Request with client-supplied correlation ID
    res = client.get(
        "/health",
        headers={"X-Correlation-ID": client_corr_id, "X-Client-Platform": "mobile-android"},
    )
    assert res.status_code == 200
    assert res.headers["X-Correlation-ID"] == client_corr_id
    assert "X-Trace-ID" in res.headers
    assert "X-Span-ID" in res.headers

    # Request without client correlation ID (must auto-generate one)
    res_auto = client.get("/health")
    assert res_auto.status_code == 200
    assert "X-Correlation-ID" in res_auto.headers
    assert res_auto.headers["X-Correlation-ID"].startswith("seva-corr-")


def test_end_to_end_traceability_across_all_six_stages():
    """Every request must be traceable across: mobile, API, agent, risk engine, clinical repo, notification."""
    res = client.post("/api/v1/observability/synthetic-probe")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "SUCCESS"
    corr_id = body["correlation_id"]

    # Query the distributed trace by correlation ID
    res_trace = client.get(f"/api/v1/observability/traces/{corr_id}")
    assert res_trace.status_code == 200
    trace = res_trace.json()

    assert trace["correlation_id"] == corr_id
    assert trace["span_count"] >= 6
    assert trace["status"] == "OK"

    # Verify all 6 mandatory stages are present in the trace
    stages = trace["stages_covered"]
    expected_stages = ["mobile", "api", "agent", "risk_engine", "clinical_repository", "notification"]
    for s in expected_stages:
        assert s in stages, f"Missing stage '{s}' in distributed trace! Stages found: {stages}"

    # Verify each span in the trace carries proper metadata
    for span in trace["spans"]:
        assert span["duration_ms"] is not None
        assert span["trace_id"] == trace["trace_id"]
        assert span["correlation_id"] == corr_id


# ==============================================================================
# 3. Operational Metrics Collection
# ==============================================================================

def test_metrics_collector_captures_all_required_domains():
    """Verifies that all 16 observability domains are recorded in MetricsCollector."""
    # 1. API
    metrics.record_api_request("POST", "/api/v1/screening", 200, 15.5)
    # 2. Errors
    metrics.record_error("VALIDATION_ERROR", "SCREENING_ENGINE", "Invalid IDRS survey input")
    # 3. Database
    metrics.record_db_query("SELECT", "citizens", 1.8, success=True)
    metrics.record_db_cache(hit=True)
    # 4. Queues
    metrics.record_queue_enqueue("triage_cases", depth=2)
    metrics.record_queue_process("triage_cases", 8.2, success=True)
    # 5. Agent
    metrics.record_agent_execution("PreventionAgent", 35.0, steps=2, escalated=False)
    # 6. LLM Latency & Failures
    metrics.record_llm_call("mock_clinical", "gemini-1.5-flash", 24.5, prompt_tokens=150, completion_tokens=75, success=True)
    metrics.record_llm_call("mock_clinical", "gemini-1.5-flash", 12.0, prompt_tokens=50, completion_tokens=0, success=False, error_reason="TIMEOUT")
    # 7. Tool Calls
    metrics.record_tool_call("get_latest_vitals", 3.2, success=True)
    # 8. Risk Engine & Model Inference
    metrics.record_risk_engine("metabolic", 14.1, risk_tier="HIGH")
    metrics.record_model_inference("calibrated_gradient_boosting_v1.0.0", 5.2, batch_size=1)
    # 9. Wearable Sync
    metrics.record_wearable_sync("APPLE_HEALTH", records_count=120, duration_ms=28.4, success=True)
    # 10. Document Pipeline
    metrics.record_document_pipeline("LAB_REPORT", duration_ms=48.2, success=True)
    # 11. Notifications
    metrics.record_notification("SMS", duration_ms=18.0, success=True)
    # 12. Audit Events
    metrics.record_audit(AuditAction.RISK_ASSESSED.value, UserRole.CLINICIAN.value, "RiskAssessment")
    # 13. Application Logs
    metrics.record_log("INFO")
    metrics.record_log("ERROR")

    summary = metrics.get_summary()

    assert summary["api"]["requests_total"] > 0
    assert summary["errors"]["total"] > 0
    assert summary["database"]["queries_total"] > 0
    assert summary["database"]["cache_hit_rate_pct"] > 0.0
    assert summary["queues"]["processed"]["triage_cases"] > 0
    assert summary["agent"]["executions_total"] > 0
    assert summary["llm"]["calls_total"] > 0
    assert summary["llm"]["failures_total"] > 0
    assert summary["llm"]["token_usage"]["total_tokens"] > 0
    assert summary["tools"]["calls_total"] > 0
    assert summary["risk_engine"]["evaluations_total"] > 0
    assert summary["model_inference"]["inferences_total"] > 0
    assert summary["wearable_sync"]["records_ingested"] > 0
    assert summary["document_pipeline"]["processed_total"] > 0
    assert summary["notifications"]["sent_total"] > 0
    assert summary["audit"]["events_total"] > 0
    assert summary["application_logs"]["INFO"] > 0


def test_latency_tracker_percentiles():
    """LatencyTracker accurately computes p50, p90, p95, p99 percentiles."""
    lt = LatencyTracker()
    for i in range(1, 101):  # 1 to 100 ms
        lt.record(float(i))

    stats = lt.stats()
    assert stats["count"] == 100
    assert stats["avg"] == 50.5
    assert stats["p50"] == 50.0
    assert stats["p90"] == 90.0
    assert stats["p95"] == 95.0
    assert stats["p99"] == 99.0
    assert stats["max"] == 100.0


# ==============================================================================
# 4. The Four Dedicated Observability Dashboards
# ==============================================================================

def test_system_health_dashboard():
    """GET /api/v1/observability/dashboards/system returns system health, latency, DB, and queue metrics."""
    res = client.get("/api/v1/observability/dashboards/system")
    assert res.status_code == 200
    data = res.json()

    assert data["dashboard_name"] == "System Health"
    assert data["status"] in ["HEALTHY", "DEGRADED", "CRITICAL"]
    assert "uptime_seconds" in data

    kpis = data["kpis"]
    assert "total_requests" in kpis
    assert "error_rate_pct" in kpis
    assert "api_latency_p50_ms" in kpis
    assert "api_latency_p95_ms" in kpis
    assert "db_queries_total" in kpis
    assert "db_active_connections" in kpis

    components = data["components"]
    assert "api_gateway" in components
    assert "database_pool" in components
    assert "message_queues" in components


def test_ai_health_dashboard():
    """GET /api/v1/observability/dashboards/ai returns agent executions, LLM latency, failures, and tokens."""
    res = client.get("/api/v1/observability/dashboards/ai")
    assert res.status_code == 200
    data = res.json()

    assert data["dashboard_name"] == "AI Health"
    assert data["status"] in ["HEALTHY", "DEGRADED", "CRITICAL"]

    kpis = data["kpis"]
    assert "agent_executions_total" in kpis
    assert "llm_calls_total" in kpis
    assert "llm_failure_rate_pct" in kpis
    assert "llm_latency_p50_ms" in kpis
    assert "total_tokens_consumed" in kpis
    assert "tool_calls_total" in kpis

    components = data["components"]
    assert "prevention_agent_runtime" in components
    assert "llm_primary_provider" in components
    assert "clinical_safety_guardrails" in components


def test_integration_health_dashboard():
    """GET /api/v1/observability/dashboards/integration returns wearable sync and notification health."""
    res = client.get("/api/v1/observability/dashboards/integration")
    assert res.status_code == 200
    data = res.json()

    assert data["dashboard_name"] == "Integration Health"
    assert data["status"] in ["HEALTHY", "DEGRADED", "CRITICAL"]

    kpis = data["kpis"]
    assert "wearable_syncs_total" in kpis
    assert "wearable_records_ingested" in kpis
    assert "wearable_error_rate_pct" in kpis
    assert "notifications_sent_total" in kpis
    assert "notifications_fail_rate_pct" in kpis

    components = data["components"]
    assert "google_fit_adapter" in components
    assert "apple_health_adapter" in components
    assert "sms_gateway_telecom" in components


def test_data_pipeline_health_dashboard():
    """GET /api/v1/observability/dashboards/pipeline returns document OCR, risk engine, and model inference."""
    res = client.get("/api/v1/observability/dashboards/pipeline")
    assert res.status_code == 200
    data = res.json()

    assert data["dashboard_name"] == "Data Pipeline Health"
    assert data["status"] in ["HEALTHY", "DEGRADED", "CRITICAL"]

    kpis = data["kpis"]
    assert "documents_processed_total" in kpis
    assert "document_fail_rate_pct" in kpis
    assert "risk_evaluations_total" in kpis
    assert "risk_engine_latency_p50_ms" in kpis
    assert "model_inferences_total" in kpis

    components = data["components"]
    assert "clinical_document_ocr" in components
    assert "fhir_r4_ingestion_pipeline" in components
    assert "ncd_risk_engine_workers" in components


def test_executive_summary_and_portal():
    """Unified summary endpoint and interactive HTML portal load cleanly."""
    res_sum = client.get("/api/v1/observability/dashboards/summary")
    assert res_sum.status_code == 200
    summary = res_sum.json()
    assert summary["overall_health"] in ["HEALTHY", "DEGRADED", "CRITICAL"]
    assert "system_health" in summary["dashboards"]
    assert "ai_health" in summary["dashboards"]
    assert "integration_health" in summary["dashboards"]
    assert "pipeline_health" in summary["dashboards"]

    # Interactive HTML Portal
    res_portal = client.get("/observability")
    assert res_portal.status_code == 200
    assert "SevaHealth AI Observability Command Center" in res_portal.text
    assert "System Health" in res_portal.text
    assert "Trace Inspector" in res_portal.text
