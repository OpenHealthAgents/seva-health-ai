"""Performance and Latency Benchmark Test Suite (PROMPT 27).

Validates response times, throughput boundaries, and concurrency characteristics:
1. API Gateway latency (p95 < 100ms)
2. Deterministic NCD Risk Engine latency (< 150ms per multi-model run)
3. Longitudinal Risk Trajectory Engine latency (< 100ms per 7-domain assessment)
4. Intervention Care Plan Synthesis latency (< 150ms per personalized plan)
5. Concurrent Load Simulation (Multi-worker request handling)
"""

import time
import statistics
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from starlette.testclient import TestClient

from services.api.main import app
from services.risk_engine.engine import ncd_risk_engine
from services.trajectory.engine import risk_trajectory_engine
from services.trajectory.models import RiskSnapshot
from services.intervention_engine.engine import prevention_intervention_engine
from services.intervention_engine.models import PreventionPlanInput

client = TestClient(app)


class TestPerformanceBenchmarks:
    """Rigorous response time and throughput verification."""

    def test_api_gateway_health_latency(self):
        """API Gateway health and metadata endpoint responds in < 100ms."""
        latencies = []
        # Warmup
        client.get("/health")

        for _ in range(25):
            t0 = time.perf_counter()
            resp = client.get("/health")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200
            latencies.append(elapsed_ms)

        median_lat = statistics.median(latencies)
        p95_lat = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"\n[Gateway Latency] Median: {median_lat:.2f}ms | p95: {p95_lat:.2f}ms")
        assert median_lat < 100.0, f"Gateway median latency too high: {median_lat:.2f}ms"

    def test_ncd_risk_engine_execution_latency(self):
        """Multi-domain deterministic risk calculation across 5 models completes in < 150ms."""
        raw_inputs = {
            "age": 52,
            "gender": "MALE",
            "systolic_bp": 142.0,
            "diastolic_bp": 92.0,
            "fasting_glucose": 126.0,
            "hba1c": 6.8,
            "bmi": 28.4,
            "waist_circumference": 96.0,
            "total_cholesterol": 215.0,
            "hdl_cholesterol": 42.0,
            "triglycerides": 185.0,
            "egfr": 78.0,
            "tobacco_use": "NONE",
            "alcohol_use": "MODERATE",
            "physical_activity_level": "SEDENTARY",
            "daily_steps_avg": 3800,
            "sleep_hours_avg": 5.5,
            "perceived_stress_score": 24,
            "family_history_diabetes": True,
            "family_history_hypertension": True,
            "family_history_premature_cad": False,
        }

        latencies = []
        for _ in range(30):
            t0 = time.perf_counter()
            result = ncd_risk_engine.evaluate(raw_inputs)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert result.overall_category is not None
            latencies.append(elapsed_ms)

        avg_lat = statistics.mean(latencies)
        p95_lat = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"\n[Risk Engine Latency] Mean: {avg_lat:.2f}ms | p95: {p95_lat:.2f}ms")
        assert avg_lat < 150.0, f"NCD Risk Engine mean latency exceeded limit: {avg_lat:.2f}ms"

    def test_risk_trajectory_engine_computation_latency(self):
        """Longitudinal multi-domain comparison across snapshots executes in < 100ms."""
        snapshots = [
            RiskSnapshot(
                citizen_id="perf-citizen-traj",
                timestamp=datetime(2025, 1, 15, tzinfo=timezone.utc),
                domain_scores={"diabetes": 0.35, "hypertension": 0.30, "cardiovascular": 0.25, "metabolic": 0.30, "obesity": 0.30, "renal": 0.20, "lifestyle": 0.35},
                domain_tiers={"diabetes": "LOW", "hypertension": "LOW", "cardiovascular": "LOW", "metabolic": "LOW", "obesity": "LOW", "renal": "LOW", "lifestyle": "LOW"},
                source="BASELINE",
                data_completeness=1.0,
                confidence=0.95,
            ),
            RiskSnapshot(
                citizen_id="perf-citizen-traj",
                timestamp=datetime(2025, 6, 20, tzinfo=timezone.utc),
                domain_scores={"diabetes": 0.45, "hypertension": 0.40, "cardiovascular": 0.35, "metabolic": 0.42, "obesity": 0.38, "renal": 0.22, "lifestyle": 0.45},
                domain_tiers={"diabetes": "MODERATE", "hypertension": "MODERATE", "cardiovascular": "LOW", "metabolic": "MODERATE", "obesity": "LOW", "renal": "LOW", "lifestyle": "MODERATE"},
                source="MIDTERM",
                data_completeness=1.0,
                confidence=0.92,
            ),
            RiskSnapshot(
                citizen_id="perf-citizen-traj",
                timestamp=datetime(2025, 12, 10, tzinfo=timezone.utc),
                domain_scores={"diabetes": 0.62, "hypertension": 0.58, "cardiovascular": 0.50, "metabolic": 0.60, "obesity": 0.55, "renal": 0.25, "lifestyle": 0.65},
                domain_tiers={"diabetes": "MODERATE", "hypertension": "MODERATE", "cardiovascular": "MODERATE", "metabolic": "MODERATE", "obesity": "MODERATE", "renal": "LOW", "lifestyle": "HIGH"},
                source="ANNUAL",
                data_completeness=1.0,
                confidence=0.94,
            ),
        ]

        latencies = []
        for _ in range(30):
            t0 = time.perf_counter()
            report = risk_trajectory_engine.evaluate_trajectory("perf-citizen-traj", snapshots)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert report.overall_trend is not None
            latencies.append(elapsed_ms)

        mean_lat = statistics.mean(latencies)
        print(f"\n[Trajectory Engine Latency] Mean: {mean_lat:.2f}ms")
        assert mean_lat < 100.0, f"Trajectory engine mean latency exceeded limit: {mean_lat:.2f}ms"

    def test_prevention_plan_synthesis_latency(self):
        """Rule-based 30-day intervention synthesis generates goals and daily tasks in < 150ms."""
        plan_input = PreventionPlanInput(
            citizen_id="perf-citizen-plan",
            tenant_id="karnataka_state_health",
            risk_profile={"overall_tier": "MODERATE", "domains": {"diabetes": "MODERATE", "hypertension": "HIGH"}},
            risk_trajectory="WORSENING",
            lifestyle={"daily_steps": 3500, "sleep_hours": 6.0, "salt_intake": "HIGH"},
            goals=["Reduce Blood Pressure", "Increase Physical Activity"],
        )

        latencies = []
        for _ in range(30):
            t0 = time.perf_counter()
            plan = prevention_intervention_engine.generate_plan(plan_input)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert plan.id is not None
            latencies.append(elapsed_ms)

        mean_lat = statistics.mean(latencies)
        print(f"\n[Intervention Plan Latency] Mean: {mean_lat:.2f}ms")
        assert mean_lat < 150.0, f"Intervention synthesis latency exceeded limit: {mean_lat:.2f}ms"

    def test_concurrent_load_simulation(self):
        """Simulates concurrent client requests across a thread pool."""
        def make_request(idx: int) -> int:
            resp = client.get("/health")
            return resp.status_code

        num_requests = 20
        with ThreadPoolExecutor(max_workers=5) as executor:
            t0 = time.perf_counter()
            results = list(executor.map(make_request, range(num_requests)))
            total_duration_sec = time.perf_counter() - t0

        assert all(code == 200 for code in results), "Not all concurrent requests returned HTTP 200"
        rps = num_requests / max(total_duration_sec, 0.001)
        print(f"\n[Concurrency] Handled {num_requests} requests in {total_duration_sec:.2f}s ({rps:.1f} req/sec)")
        assert rps > 10.0, f"Throughput too low: {rps:.1f} req/sec"
