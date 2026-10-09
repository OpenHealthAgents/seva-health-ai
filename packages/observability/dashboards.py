"""Health Dashboard Generators for SevaHealth AI.

Generates real-time health scorecards and operational telemetry for:
1. System Health Dashboard
2. AI Health Dashboard
3. Integration Health Dashboard
4. Data Pipeline Health Dashboard
"""

import time
from typing import Dict, Any, List
from packages.observability.metrics import metrics
from packages.observability.tracer import trace_store


class HealthDashboardService:
    """Computes real-time health status, SLIs/SLOs, and operational summaries."""

    @classmethod
    def get_system_health(cls) -> Dict[str, Any]:
        """System Health Dashboard: API gateway, latency, errors, DB, queues."""
        summary = metrics.get_summary()
        api = summary["api"]
        errors = summary["errors"]
        db = summary["database"]
        queues = summary["queues"]

        total_req = api["requests_total"]
        error_rate_pct = round((errors["total"] / total_req * 100), 2) if total_req > 0 else 0.0

        p95 = api["latency_stats"]["p95"]
        db_p95 = db["latency_stats"]["p95"]

        # Health status evaluation
        if error_rate_pct >= 5.0 or p95 >= 1500.0:
            status = "CRITICAL"
        elif error_rate_pct >= 1.0 or p95 >= 500.0:
            status = "DEGRADED"
        else:
            status = "HEALTHY"

        total_queue_depth = sum(queues["current_depths"].values())

        return {
            "dashboard_name": "System Health",
            "status": status,
            "timestamp": time.time(),
            "uptime_seconds": summary["uptime_seconds"],
            "kpis": {
                "total_requests": total_req,
                "error_rate_pct": error_rate_pct,
                "api_latency_p50_ms": api["latency_stats"]["p50"],
                "api_latency_p95_ms": p95,
                "api_latency_p99_ms": api["latency_stats"]["p99"],
                "db_queries_total": db["queries_total"],
                "db_latency_avg_ms": db["latency_stats"]["avg"],
                "db_active_connections": db["active_connections"],
                "db_cache_hit_rate_pct": db["cache_hit_rate_pct"],
                "total_queue_backlog": total_queue_depth,
            },
            "components": {
                "api_gateway": "OPERATIONAL" if error_rate_pct < 5.0 else "DEGRADED",
                "database_pool": "OPERATIONAL" if db_p95 < 200.0 else "SLOW",
                "message_queues": "HEALTHY" if total_queue_depth < 100 else "BACKLOG_ELEVATED",
                "auth_service": "OPERATIONAL",
            },
            "breakdown": {
                "requests_by_status": api["requests_by_status"],
                "top_active_routes": api["top_routes"],
                "errors_by_component": errors["by_component"],
                "queue_depths": queues["current_depths"],
            },
        }

    @classmethod
    def get_ai_health(cls) -> Dict[str, Any]:
        """AI Health Dashboard: Agent executions, LLM latency, failures, tokens, tools."""
        summary = metrics.get_summary()
        agent = summary["agent"]
        llm = summary["llm"]
        tools = summary["tools"]

        total_llm = llm["calls_total"]
        llm_failures = llm["failures_total"]
        llm_failure_rate_pct = round((llm_failures / total_llm * 100), 2) if total_llm > 0 else 0.0

        p95_llm = llm["latency_stats"]["p95"]

        if llm_failure_rate_pct >= 5.0 or p95_llm >= 4000.0:
            status = "CRITICAL"
        elif llm_failure_rate_pct >= 1.0 or p95_llm >= 2000.0:
            status = "DEGRADED"
        else:
            status = "HEALTHY"

        tool_calls = tools["calls_total"]
        tool_fails = sum(tools["failures_by_name"].values())
        tool_failure_rate_pct = round((tool_fails / tool_calls * 100), 2) if tool_calls > 0 else 0.0

        return {
            "dashboard_name": "AI Health",
            "status": status,
            "timestamp": time.time(),
            "kpis": {
                "agent_executions_total": agent["executions_total"],
                "agent_latency_avg_ms": agent["latency_stats"]["avg"],
                "agent_escalations_total": agent["escalations_total"],
                "llm_calls_total": total_llm,
                "llm_failure_rate_pct": llm_failure_rate_pct,
                "llm_latency_p50_ms": llm["latency_stats"]["p50"],
                "llm_latency_p95_ms": p95_llm,
                "total_tokens_consumed": llm["token_usage"]["total_tokens"],
                "prompt_tokens": llm["token_usage"]["prompt_tokens"],
                "completion_tokens": llm["token_usage"]["completion_tokens"],
                "tool_calls_total": tool_calls,
                "tool_failure_rate_pct": tool_failure_rate_pct,
            },
            "components": {
                "prevention_agent_runtime": "OPERATIONAL",
                "llm_primary_provider": "HEALTHY" if llm_failure_rate_pct < 2.0 else "DEGRADED",
                "clinical_safety_guardrails": "ENFORCING",
                "mcp_tools_bridge": "OPERATIONAL" if tool_failure_rate_pct < 5.0 else "DEGRADED",
            },
            "breakdown": {
                "calls_by_model": llm["calls_by_model"],
                "failures_by_reason": llm["failures_by_reason"],
                "top_tools_called": dict(sorted(tools["calls_by_name"].items(), key=lambda x: x[1], reverse=True)[:5]),
                "tool_failures": tools["failures_by_name"],
            },
        }

    @classmethod
    def get_integration_health(cls) -> Dict[str, Any]:
        """Integration Health Dashboard: Wearables, notifications, external gateways."""
        summary = metrics.get_summary()
        wearables = summary["wearable_sync"]
        notifications = summary["notifications"]

        total_syncs = wearables["syncs_total"]
        sync_errors = wearables["errors_total"]
        wearable_error_rate_pct = round((sync_errors / total_syncs * 100), 2) if total_syncs > 0 else 0.0

        total_notifs = notifications["sent_total"] + notifications["failed_total"]
        notif_fail_rate_pct = round((notifications["failed_total"] / total_notifs * 100), 2) if total_notifs > 0 else 0.0

        if wearable_error_rate_pct >= 10.0 or notif_fail_rate_pct >= 10.0:
            status = "CRITICAL"
        elif wearable_error_rate_pct >= 3.0 or notif_fail_rate_pct >= 3.0:
            status = "DEGRADED"
        else:
            status = "HEALTHY"

        return {
            "dashboard_name": "Integration Health",
            "status": status,
            "timestamp": time.time(),
            "kpis": {
                "wearable_syncs_total": total_syncs,
                "wearable_records_ingested": wearables["records_ingested"],
                "wearable_error_rate_pct": wearable_error_rate_pct,
                "wearable_sync_latency_p50_ms": wearables["latency_stats"]["p50"],
                "notifications_sent_total": notifications["sent_total"],
                "notifications_failed_total": notifications["failed_total"],
                "notifications_fail_rate_pct": notif_fail_rate_pct,
                "notification_latency_avg_ms": notifications["latency_stats"]["avg"],
            },
            "components": {
                "google_fit_adapter": "CONNECTED",
                "apple_health_adapter": "CONNECTED",
                "ble_peripheral_bridge": "ONLINE",
                "sms_gateway_telecom": "HEALTHY" if notif_fail_rate_pct < 5.0 else "DEGRADED",
                "whatsapp_business_api": "HEALTHY",
                "abdm_m1_m2_gateway": "ONLINE (SANDBOX_ACTIVE)",
            },
            "breakdown": {
                "wearable_sync_by_device": wearables["by_device"],
                "notifications_by_channel": notifications["by_channel"],
            },
        }

    @classmethod
    def get_data_pipeline_health(cls) -> Dict[str, Any]:
        """Data Pipeline Health Dashboard: Document pipeline, risk engine, model inference."""
        summary = metrics.get_summary()
        docs = summary["document_pipeline"]
        risk = summary["risk_engine"]
        inference = summary["model_inference"]

        total_docs = docs["processed_total"] + docs["failed_total"]
        doc_fail_rate_pct = round((docs["failed_total"] / total_docs * 100), 2) if total_docs > 0 else 0.0

        risk_evals = risk["evaluations_total"]
        risk_p95 = risk["latency_stats"]["p95"]

        if doc_fail_rate_pct >= 10.0 or risk_p95 >= 1000.0:
            status = "CRITICAL"
        elif doc_fail_rate_pct >= 3.0 or risk_p95 >= 400.0:
            status = "DEGRADED"
        else:
            status = "HEALTHY"

        return {
            "dashboard_name": "Data Pipeline Health",
            "status": status,
            "timestamp": time.time(),
            "kpis": {
                "documents_processed_total": docs["processed_total"],
                "documents_failed_total": docs["failed_total"],
                "document_ocr_latency_avg_ms": docs["latency_stats"]["avg"],
                "document_fail_rate_pct": doc_fail_rate_pct,
                "risk_evaluations_total": risk_evals,
                "risk_engine_latency_p50_ms": risk["latency_stats"]["p50"],
                "risk_engine_latency_p95_ms": risk_p95,
                "model_inferences_total": inference["inferences_total"],
                "inference_latency_avg_ms": inference["latency_stats"]["avg"],
            },
            "components": {
                "clinical_document_ocr": "HEALTHY" if doc_fail_rate_pct < 5.0 else "DEGRADED",
                "fhir_r4_ingestion_pipeline": "OPERATIONAL",
                "ncd_risk_engine_workers": "HEALTHY" if risk_p95 < 500.0 else "SLOW",
                "calibrated_model_inference_pool": "OPERATIONAL",
            },
            "breakdown": {
                "documents_by_type": docs["by_type"],
                "risk_evaluations_by_domain": risk["by_domain"],
                "risk_tier_distribution": risk["tier_distribution"],
                "inferences_by_model_version": inference["by_version"],
            },
        }

    @classmethod
    def get_unified_summary(cls) -> Dict[str, Any]:
        """Unified executive overview of all 4 dashboards."""
        sys_h = cls.get_system_health()
        ai_h = cls.get_ai_health()
        int_h = cls.get_integration_health()
        pipe_h = cls.get_data_pipeline_health()

        statuses = [sys_h["status"], ai_h["status"], int_h["status"], pipe_h["status"]]
        overall = "CRITICAL" if "CRITICAL" in statuses else ("DEGRADED" if "DEGRADED" in statuses else "HEALTHY")

        recent_traces = trace_store.list_recent_traces(limit=10)

        return {
            "overall_health": overall,
            "timestamp": time.time(),
            "dashboards": {
                "system_health": {"status": sys_h["status"], "kpis": sys_h["kpis"]},
                "ai_health": {"status": ai_h["status"], "kpis": ai_h["kpis"]},
                "integration_health": {"status": int_h["status"], "kpis": int_h["kpis"]},
                "pipeline_health": {"status": pipe_h["status"], "kpis": pipe_h["kpis"]},
            },
            "recent_traces_count": len(recent_traces),
            "recent_traces": recent_traces,
        }
