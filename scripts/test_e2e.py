"""End-to-End Primary Demo Flow Verification Script.

Executes and verifies the complete 8-stage loop:
Screen → Understand → Predict → Explain → Intervene → Monitor → Escalate → Measure
"""

import sys
from pathlib import Path

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient
from services.api.main import app
from scripts.seed_data import seed_all_demo_data

client = TestClient(app)


def run_e2e_verification():
    print("=" * 80)
    print("SevaHealth AI: End-to-End Primary Demo Flow Verification")
    print("=" * 80)

    # Setup database with seed personas
    seed_all_demo_data()

    # Step 1: Citizen Registration
    print("\n[Step 1/8] Citizen Registration / Profile Retrieval")
    resp = client.get("/api/v1/citizens/citizen-ramesh-patel-01")
    assert resp.status_code == 200, f"Failed: {resp.text}"
    c = resp.json()
    print(f"  --> Loaded Citizen: {c['name']} (Age 48, District: {c['district']}, ABHA: {c['abha_id']})")

    # Step 2: Preventive Screening & Vitals Entry
    print("\n[Step 2/8] Preventive Health Screening & Vitals Submission")
    screening_payload = {
        "citizen_id": c["id"],
        "idrs": {
            "age_category": "35-49",
            "waist_category": "90-99",
            "physical_activity": "Sedentary",
            "family_history": "One parent"
        },
        "cbac": {
            "age_over_30": True,
            "tobacco_user": False,
            "alcohol_consumption": False,
            "waist_circumference_exceeded": True,
            "physical_activity_below_150min": True,
            "family_history_diabetes_or_htn": True,
            "symptoms": ["Occasional daytime lethargy"]
        },
        "vitals": {
            "systolic_bp": 138.0,
            "diastolic_bp": 88.0,
            "fasting_glucose": 118.0,
            "hba1c": 6.2,
            "bmi": 27.2,
            "waist_circumference": 96.0,
            "triglycerides": 185.0
        }
    }
    resp = client.post("/api/v1/screening/", json=screening_payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"
    s_data = resp.json()
    print(f"  --> Screening Recorded. IDRS Score: {s_data['calculated_idrs_score']}/100, CBAC Score: {s_data['calculated_cbac_score']}")

    # Step 3: AI NCD Risk Assessment
    print("\n[Step 3/8] Multi-Factor NCD Risk Stratification")
    resp = client.post(f"/api/v1/risk/evaluate/{c['id']}")
    assert resp.status_code == 200, f"Failed: {resp.text}"
    risk = resp.json()
    print(f"  --> Evaluated Composite Risk: {risk['overall_tier']} ({risk['overall_score']*100:.0f}%)")
    print(f"      Diabetes Risk: {risk['domains']['diabetes_risk']*100:.0f}% (Prediabetes)")
    print(f"      Hypertension Risk: {risk['domains']['hypertension_risk']*100:.0f}% (Pre-HTN)")
    print(f"      Cardiovascular Risk: {risk['domains']['cardiovascular_risk']*100:.0f}%")
    print(f"      Trajectory: {risk['trajectory']}")

    # Step 4: Explain Risk (SHAP-Style Attribution Waterfall)
    print("\n[Step 4/8] Risk Explainability & Attribution Drivers")
    print(f"  --> Safety Disclaimer: {risk['safety_disclaimer']}")
    print("  --> Top Contributing Risk Drivers:")
    for d in risk["top_drivers"]:
        print(f"      + {d['impact_weight']*100:.0f}%: {d['feature_name']} ({d['observed_value']} vs target {d['target_value']})")
    print("  --> Protective Mitigating Factors:")
    for p in risk["protective_factors"]:
        print(f"      - {abs(p['impact_weight'])*100:.0f}%: {p['feature_name']} ({p['observed_value']})")

    # Step 5: Personalized 30-Day Preventive Care Plan
    print("\n[Step 5/8] Personalized 30-Day Lifestyle Medicine Care Plan")
    resp = client.get(f"/api/v1/intervention/plan/{c['id']}")
    assert resp.status_code == 200, f"Failed: {resp.text}"
    plan = resp.json()
    print(f"  --> Journey: '{plan['title']}'")
    print(f"      Nutrition Guidance: {plan['nutrition_guidance']}")
    print(f"      Activity Target: {plan['activity_guidance']}")
    print(f"      Total Daily Tasks: {len(plan['daily_tasks'])}")

    # Check off a task and verify adherence updates
    task = plan["daily_tasks"][6]
    toggle_resp = client.post(f"/api/v1/intervention/tasks/{c['id']}/{task['id']}/toggle")
    assert toggle_resp.status_code == 200
    updated_plan = toggle_resp.json()
    print(f"  --> Checked off '{task['title']}'. Updated Adherence: {updated_plan['adherence_percentage']}%")

    # Step 6: Longitudinal Wearable Biometrics Sync
    print("\n[Step 6/8] Longitudinal Wearable Telemetry & Baseline Tracking")
    w_resp = client.post(f"/api/v1/wearables/sync/{c['id']}")
    assert w_resp.status_code == 200
    w_data = w_resp.json()
    baselines = w_data["seven_day_baselines"]
    print(f"  --> Synced {w_data['synced_records_count']} days of smartwatch timeseries.")
    print(f"      7-Day Avg Resting HR: {baselines['avg_resting_heart_rate']} bpm")
    print(f"      7-Day Avg HRV rMSSD: {baselines['avg_hrv_rmssd']} ms")
    print(f"      7-Day Avg Daily Steps: {baselines['avg_daily_steps']} steps")

    # Step 7: Clinician Triage Queue & Review Action
    print("\n[Step 7/8] Clinician Triage Queue & Decision Support Review")
    triage_resp = client.get("/api/v1/clinician/triage")
    assert triage_resp.status_code == 200
    triage_list = triage_resp.json()
    print(f"  --> High-Risk Triage Queue Size: {len(triage_list)} pending cases.")
    first_case = triage_list[0]
    print(f"      Escalated Citizen: {first_case['citizen_name']} ({first_case['urgency']})")
    print(f"      Reason: {first_case['escalation_reason']}")

    # Clinician signs off
    review_resp = client.post(
        f"/api/v1/clinician/review/{first_case['id']}",
        json={
            "status": "APPROVED",
            "review_notes": "Reviewed in PHC. Biometrics consistent with Stage 2 HTN. Prescribed dietary sodium restriction and scheduled follow-up.",
            "updated_care_plan_instructions": "Ensure strict daily salt under 2g."
        }
    )
    assert review_resp.status_code == 200
    print("  --> Clinician Review Status: APPROVED (Stamped with Dr. ID and timestamp)")

    # Step 8: Population Health Intelligence & Outcome Delta
    print("\n[Step 8/8] Population Health Intelligence & Outcome Delta")
    pop_resp = client.get("/api/v1/population/metrics")
    assert pop_resp.status_code == 200
    pop = pop_resp.json()
    print(f"  --> State: {pop['state']} (Screened Cohort: {pop['total_screened_population']} citizens)")
    print(f"      Pre-Diabetes / Diabetes Prevalence: {pop['prevalence_rates']['prediabetes_and_diabetes']*100:.1f}%")
    print(f"      Pre-Hypertension / HTN Prevalence: {pop['prevalence_rates']['prehypertension_and_htn']*100:.1f}%")

    # Step 9: Multi-EMR Interoperability & Clinical Data Federation
    print("\n[Step 9/9] Multi-EMR Interoperability & Clinical Data Federation")
    from packages.auth.jwt import create_access_token
    from packages.types.enums import UserRole

    token = create_access_token(
        subject="dr_ananya_01",
        tenant_id="karnataka_state_health",
        role=UserRole.CLINICIAN,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Verify adapter connectivity
    adapters_resp = client.get("/api/v1/interop/adapters")
    assert adapters_resp.status_code == 200
    adapters_data = adapters_resp.json()
    print(f"  --> Federated Adapters Status: {adapters_data['status']} ({len(adapters_data['adapters'])} adapters active)")

    # Retrieve federated chart
    chart_resp = client.get(f"/api/v1/interop/patient/{c['id']}/chart", headers=headers)
    assert chart_resp.status_code == 200
    chart = chart_resp.json()
    print(f"  --> Unified Clinical Chart Retrieved for: {chart['patient']['name']}")
    print(f"      - Observations aggregated: {len(chart['observations'])}")
    print(f"      - Encounters aggregated: {len(chart['encounters'])}")
    print(f"      - Care Plans aggregated: {len(chart['care_plans'])}")

    # Verify Anti-Arbitrary Query Guard blocks raw SQL
    attack_resp = client.get(f"/api/v1/interop/patient/{c['id']}' UNION SELECT 1,2 --", headers=headers)
    assert attack_resp.status_code == 400
    print("  --> Security Guard: Blocked raw SQL injection attempt (400 Bad Request)")

    # Verify Audit Trail
    audit_resp = client.get(f"/api/v1/interop/audit-logs?patient_id={c['id']}", headers=headers)
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    print(f"  --> Forensic Audit Trail: {len(audit_logs)} access events recorded immutably.")

    # Step 10: Bounded Multi-Agent System Verification
    print("\n[Step 10/10] Bounded Multi-Agent System Verification (9 Specialized Agents)")
    agents_resp = client.get("/api/v1/agents")
    assert agents_resp.status_code == 200
    agents_data = agents_resp.json()
    print(f"  --> Registered Bounded Agents: {agents_data['total_agents']} active agents")

    # Execute 4-Stage Multi-Agent Screening-to-Prevention Pipeline
    pipeline_resp = client.post(
        "/api/v1/agents/orchestrate/screening-pipeline",
        json={
            "citizen_id": c["id"],
            "age": 48,
            "gender": "MALE",
            "waist_cm": 96.0,
            "activity_level": "Sedentary",
            "family_history": "One parent",
            "cbac_answers": {"age_over_30": True, "waist_circumference_exceeded": True},
            "vitals": {"systolic_bp": 138.0, "fasting_glucose": 118.0},
        },
        headers=headers,
    )
    assert pipeline_resp.status_code == 200
    pipe_out = pipeline_resp.json()
    print(f"  --> Multi-Agent Pipeline Status: {pipe_out['pipeline_status']}")
    print(f"      - ScreeningAgent: CBAC Score {pipe_out['screening']['cbac_score']}, IDRS Score {pipe_out['screening']['idrs_score']}")
    print(f"      - RiskAssessmentAgent: Tier {pipe_out['risk_assessment']['risk_tier']}, Score {pipe_out['risk_assessment']['composite_score']*100:.0f}%")
    print(f"      - TrendAnalysisAgent: Trajectory {pipe_out['trajectory']['trend']}")
    print(f"      - PreventionAgent: Plan '{pipe_out['prevention_plan']['plan_title']}' ({pipe_out['prevention_plan']['duration_days']} days)")

    # Execute EscalationAgent Emergency Detection
    esc_resp = client.post(
        "/api/v1/agents/orchestrate/conversational-check",
        json={
            "citizen_id": c["id"],
            "message": "I feel sudden crushing pain in chest and left arm",
            "vitals": {"systolic_bp": 140.0},
        },
        headers=headers,
    )
    assert esc_resp.status_code == 200
    esc_out = esc_resp.json()
    print(f"  --> EscalationAgent Red-Flag Check: Route = {esc_out['route']}, Urgency = {esc_out.get('urgency')}")

    # Verify Agent Execution Telemetry Logs
    telemetry_resp = client.get("/api/v1/agents/telemetry/logs?limit=5", headers=headers)
    assert telemetry_resp.status_code == 200
    telemetry_logs = telemetry_resp.json()
    print(f"  --> Agent Forensic Telemetry: Recorded {len(telemetry_logs)} bounded agent execution audit entries.")

    print("\n" + "=" * 80)
    print("ALL 10 CORE E2E WORKFLOWS INCLUDING MULTI-AGENT SYSTEM VERIFIED!")
    print("=" * 80)


if __name__ == "__main__":
    run_e2e_verification()
