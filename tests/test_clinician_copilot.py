"""Comprehensive Test Suite for SevaHealth AI Clinician Copilot.

Verifies:
1. Patient Summary Assembly across all 11 required dimensions:
   - Current risks, Risk trajectory, Recent vitals, Recent labs,
   - Wearable trends, Lifestyle, Medications, Adherence,
   - Interventions, Alerts, Documents.
2. AI Copilot Synthesis with all 7 required outputs:
   - Clinical summary, Risk summary, Recent changes, Missing information,
   - Possible contributing factors, Suggested follow-up,
   - Questions for clinician consideration.
3. Prominent labeling: AI-GENERATED vs CLINICIAN-VERIFIED.
4. Clinician action lifecycle:
   - ACCEPT, EDIT, REJECT, ADD_COMMENT, CREATE_CARE_PLAN, REFER, ESCALATE.
5. Strict Legal Record Protection:
   - Unverified AI conclusions are NEVER written into the legal clinical record.
   - Rejected drafts are strictly excluded from the legal clinical record.
   - Only explicit clinician confirmation promotes records into the legal clinical record.
6. Access control and role authorization (CLINICIAN only).
"""

import pytest
from starlette.testclient import TestClient

from packages.types.enums import UserRole, TriageUrgency
from packages.auth.jwt import TokenPayload, create_access_token
from services.api.main import app
from services.store import store
from scripts.seed_data import seed_all_demo_data
from services.clinical.copilot import (
    ClinicianCopilotEngine,
    ClinicianCopilotPatientView,
    AICopilotSynthesis,
    ClinicianActionPayload,
    ClinicianVerificationRecord,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_seed():
    """Seed fresh demo personas and clean records before each test."""
    store.legal_clinical_records.clear()
    store.copilot_drafts.clear()
    store.referrals.clear()
    seed_all_demo_data()


@pytest.fixture
def doctor_actor():
    return TokenPayload(
        sub="doctor-user-01",
        tenant_id="karnataka_state_health",
        role=UserRole.CLINICIAN,
    )


@pytest.fixture
def citizen_actor():
    return TokenPayload(
        sub="citizen-user-01",
        tenant_id="karnataka_state_health",
        role=UserRole.CITIZEN,
    )


class TestClinicianCopilotPatientSummary:
    """Verifies that the clinician sees all 11 required patient summary dimensions."""

    def test_assemble_all_11_patient_dimensions(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"
        view = ClinicianCopilotEngine.assemble_patient_summary(cid, doctor_actor)

        assert isinstance(view, ClinicianCopilotPatientView)
        assert view.citizen_id == cid

        # 1. Profile
        assert view.patient_profile["name"] == "Ramesh Patel"
        assert view.patient_profile["age"] >= 40

        # 2. Current risks
        assert view.current_risks["overall_tier"] == "HIGH"
        assert view.current_risks["overall_score"] > 0.60
        assert "diabetes_risk" in view.current_risks["domains"]

        # 3. Risk trajectory
        assert view.risk_trajectory["trend_status"] in ["WORSENING", "DETERIORATING"]
        assert len(view.risk_trajectory["contributing_factors"]) > 0

        # 4. Recent vitals
        assert "systolic_bp" in view.recent_vitals
        assert view.recent_vitals["systolic_bp"]["value"] == 138.0
        assert view.recent_vitals["systolic_bp"]["unit"] == "mmHg"

        # 5. Recent labs
        assert "hba1c" in view.recent_labs
        assert view.recent_labs["hba1c"]["value"] == 6.2
        assert "fasting_glucose" in view.recent_labs

        # 6. Wearable trends
        assert view.wearable_trends["connection_status"] == "CONNECTED"
        assert view.wearable_trends["seven_day_baselines"]["avg_daily_steps"] is not None

        # 7. Lifestyle
        assert view.lifestyle["dietary_pattern"] == "HIGH_CARB_HIGH_SALT"
        assert view.lifestyle["tobacco_use"] == "NEVER"

        # 8. Medications
        assert len(view.medications) >= 2
        med_names = [m["drug_name"] for m in view.medications]
        assert "Metformin" in med_names
        assert "Telmisartan" in med_names

        # 9. Adherence
        assert view.adherence["adherence_percentage"] == 20.0
        assert view.adherence["recent_checkins_count"] >= 1

        # 10. Interventions
        assert "daily_tasks" in view.interventions or "current_week_tasks" in view.interventions
        assert view.interventions["duration_days"] == 30

        # 11. Alerts & Documents
        assert len(view.alerts) >= 1
        assert view.alerts[0]["urgency"] == "PRIORITY"
        assert len(view.documents) >= 1
        assert "Annual_NCD_Screening_Report_2026.pdf" in view.documents[0]["file_name"]


class TestAICopilotSynthesis:
    """Verifies that the AI generates all 7 required decision-support sections with proper labeling."""

    def test_generate_all_7_ai_sections_with_labeling(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"
        synthesis = ClinicianCopilotEngine.generate_copilot_synthesis(cid, doctor_actor)

        assert isinstance(synthesis, AICopilotSynthesis)

        # Explicit Labels
        assert synthesis.label == "AI-GENERATED"
        assert synthesis.verification_status == "DRAFT_PENDING_CLINICIAN_VERIFICATION"
        assert synthesis.is_committed_to_legal_record is False

        # 1. Clinical summary
        assert "Ramesh Patel" in synthesis.clinical_summary
        assert "138/88" in synthesis.clinical_summary or "blood pressure" in synthesis.clinical_summary

        # 2. Risk summary
        assert "HIGH" in synthesis.risk_summary
        assert "ICMR" in synthesis.risk_summary

        # 3. Recent changes
        assert "Longitudinal" in synthesis.recent_changes
        assert "trajectory" in synthesis.recent_changes.lower() or "steps" in synthesis.recent_changes.lower()

        # 4. Missing information
        assert isinstance(synthesis.missing_information, list)
        assert len(synthesis.missing_information) >= 1

        # 5. Possible contributing factors
        assert isinstance(synthesis.possible_contributing_factors, list)
        assert len(synthesis.possible_contributing_factors) >= 1
        assert any("associated with" in f.lower() or "contributing" in f.lower() for f in synthesis.possible_contributing_factors)

        # 6. Suggested follow-up
        assert isinstance(synthesis.suggested_follow_up, list)
        assert len(synthesis.suggested_follow_up) >= 2

        # 7. Questions for clinician consideration
        assert isinstance(synthesis.questions_for_clinician_consideration, list)
        assert len(synthesis.questions_for_clinician_consideration) >= 3


class TestClinicianActionGovernance:
    """Verifies clinician actions (accept, edit, reject, comment, create care plan, refer, escalate)

    and strict legal medical record protection.
    """

    def test_unverified_draft_is_never_in_legal_record(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"

        # Initially no legal record exists
        initial_legal = store.get_legal_clinical_records(cid)
        assert len(initial_legal) == 0

        # Generating an AI synthesis creates a draft in memory ONLY
        synthesis = ClinicianCopilotEngine.generate_copilot_synthesis(cid, doctor_actor)
        assert synthesis.is_committed_to_legal_record is False

        # Verify that generating draft DID NOT write into legal clinical record
        legal_after_gen = store.get_legal_clinical_records(cid)
        assert len(legal_after_gen) == 0, "AI draft must never be written automatically to legal record!"

    def test_action_accept_promotes_to_legal_record_with_signature(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"

        record = ClinicianCopilotEngine.process_clinician_action(
            citizen_id=cid,
            action_payload=ClinicianActionPayload(action="ACCEPT"),
            actor=doctor_actor,
        )

        assert record.label == "CLINICIAN-VERIFIED"
        assert record.status == "ACCEPTED"
        assert record.legal_record_committed is True
        assert record.verified_by_doctor_id == "doctor-user-01"
        assert record.digital_signature_hash != ""

        # Legal record now contains exactly 1 verified encounter
        legal_records = store.get_legal_clinical_records(cid)
        assert len(legal_records) == 1
        assert legal_records[0]["label"] == "CLINICIAN-VERIFIED"
        assert legal_records[0]["digital_signature_hash"] == record.digital_signature_hash

    def test_action_edit_modifies_conclusion_and_commits_to_legal_record(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"

        custom_summary = "Patient evaluated in clinic. Biometrics confirm Stage 1 HTN and prediabetes. Clinician verified."
        custom_plan = "Initiate dietary sodium restriction < 2g and foxtail millet. Review in 30 days."

        record = ClinicianCopilotEngine.process_clinician_action(
            citizen_id=cid,
            action_payload=ClinicianActionPayload(
                action="EDIT",
                edited_clinical_summary=custom_summary,
                edited_plan=custom_plan,
            ),
            actor=doctor_actor,
        )

        assert record.label == "CLINICIAN-VERIFIED"
        assert record.status == "MODIFIED"
        assert record.final_clinical_summary == custom_summary
        assert record.final_clinical_plan == custom_plan

        # Legal record updated with clinician edits
        legal = store.get_legal_clinical_records(cid)
        assert len(legal) == 1
        assert legal[0]["final_clinical_summary"] == custom_summary

    def test_action_reject_discards_draft_and_never_writes_to_legal_record(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"

        record = ClinicianCopilotEngine.process_clinician_action(
            citizen_id=cid,
            action_payload=ClinicianActionPayload(
                action="REJECT",
                rejection_reason="Patient was acutely febrile during screening; biometric spikes are transient and unrepresentative.",
            ),
            actor=doctor_actor,
        )

        assert record.status == "REJECTED"
        assert record.legal_record_committed is False

        # Strictly 0 records in legal clinical record!
        legal = store.get_legal_clinical_records(cid)
        assert len(legal) == 0, "Rejected AI conclusions must never appear in legal clinical record!"

    def test_action_add_comment(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"

        record = ClinicianCopilotEngine.process_clinician_action(
            citizen_id=cid,
            action_payload=ClinicianActionPayload(
                action="ADD_COMMENT",
                clinician_comments="Patient denies headache or chest pain. Family history positive for Type 2 Diabetes.",
            ),
            actor=doctor_actor,
        )

        assert record.status == "COMMENTED"
        assert record.legal_record_committed is True
        assert "Family history positive" in record.final_clinical_plan

    def test_action_create_care_plan(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"

        record = ClinicianCopilotEngine.process_clinician_action(
            citizen_id=cid,
            action_payload=ClinicianActionPayload(
                action="CREATE_CARE_PLAN",
                care_plan_title="Doctor Prescribed 30-Day Millet & Activity Regimen",
                dietary_prescription="Replace white rice with Siridhanya millets; eliminate processed sugar.",
                activity_prescription="25 minutes morning brisk walk daily.",
            ),
            actor=doctor_actor,
        )

        assert record.status == "CARE_PLAN_CREATED"
        assert record.active_care_plan_id is not None

        # Verify plan was set in store
        plan = store.get_care_plan(cid)
        assert plan is not None
        assert plan.title == "Doctor Prescribed 30-Day Millet & Activity Regimen"
        assert plan.clinician_reviewed is True

    def test_action_refer(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"

        record = ClinicianCopilotEngine.process_clinician_action(
            citizen_id=cid,
            action_payload=ClinicianActionPayload(
                action="REFER",
                referral_facility="District Hospital Diabetology Clinic",
                referral_urgency=TriageUrgency.URGENT,
                referral_reason="Progressive prediabetes with elevated visceral adiposity",
            ),
            actor=doctor_actor,
        )

        assert record.status == "REFERRED"
        assert record.active_referral_id is not None

        # Verify referral in store
        refs = store.get_referrals(cid)
        assert len(refs) >= 1
        assert refs[0]["referred_to_facility"] == "District Hospital Diabetology Clinic"
        assert refs[0]["urgency"] == "URGENT"

    def test_action_escalate(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"

        record = ClinicianCopilotEngine.process_clinician_action(
            citizen_id=cid,
            action_payload=ClinicianActionPayload(
                action="ESCALATE",
                escalation_urgency=TriageUrgency.EMERGENT,
                escalation_reason="Severe blood pressure spike observed with deteriorating trend",
            ),
            actor=doctor_actor,
        )

        assert record.status == "ESCALATED"
        assert record.active_alert_id is not None

        # Verify emergency alert in store
        alerts = store.get_alerts(cid)
        assert len(alerts) >= 1
        assert any(a["urgency"] == "EMERGENT" for a in alerts)


class TestClinicianCopilotAPIEndpoints:
    """Verifies FastAPI router endpoints for Clinician Copilot."""

    def test_api_patient_summary_endpoint_success(self, doctor_actor):
        token = create_access_token(
            subject=doctor_actor.sub,
            tenant_id=doctor_actor.tenant_id,
            role=doctor_actor.role,
        )

        resp = client.get(
            "/api/v1/clinician/copilot/patient-summary/citizen-ramesh-patel-01",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["citizen_id"] == "citizen-ramesh-patel-01"
        assert "patient_profile" in data
        assert "current_risks" in data
        assert "recent_vitals" in data
        assert "recent_labs" in data
        assert "wearable_trends" in data
        assert "lifestyle" in data
        assert "medications" in data
        assert "adherence" in data
        assert "interventions" in data
        assert "alerts" in data
        assert "documents" in data

    def test_api_generate_copilot_endpoint(self, doctor_actor):
        token = create_access_token(
            subject=doctor_actor.sub,
            tenant_id=doctor_actor.tenant_id,
            role=doctor_actor.role,
        )

        resp = client.post(
            "/api/v1/clinician/copilot/generate/citizen-ramesh-patel-01",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "AI-GENERATED"
        assert data["verification_status"] == "DRAFT_PENDING_CLINICIAN_VERIFICATION"
        assert data["clinical_summary"] != ""
        assert data["risk_summary"] != ""
        assert data["recent_changes"] != ""
        assert len(data["missing_information"]) > 0
        assert len(data["possible_contributing_factors"]) > 0
        assert len(data["suggested_follow_up"]) > 0
        assert len(data["questions_for_clinician_consideration"]) > 0

    def test_api_action_accept_and_legal_record_retrieval(self, doctor_actor):
        cid = "citizen-ramesh-patel-01"
        token = create_access_token(
            subject=doctor_actor.sub,
            tenant_id=doctor_actor.tenant_id,
            role=doctor_actor.role,
        )

        # 1. Execute ACCEPT
        action_resp = client.post(
            f"/api/v1/clinician/copilot/action/{cid}",
            json={"action": "ACCEPT"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert action_resp.status_code == 200
        rec = action_resp.json()
        assert rec["label"] == "CLINICIAN-VERIFIED"
        assert rec["status"] == "ACCEPTED"
        assert rec["legal_record_committed"] is True

        # 2. Retrieve legal records
        legal_resp = client.get(
            f"/api/v1/clinician/copilot/legal-record/{cid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert legal_resp.status_code == 200
        leg = legal_resp.json()
        assert leg["total_records"] >= 1
        assert leg["records"][0]["label"] == "CLINICIAN-VERIFIED"

    def test_api_rejects_unauthorized_citizen_role(self, citizen_actor):
        token = create_access_token(
            subject=citizen_actor.sub,
            tenant_id=citizen_actor.tenant_id,
            role=citizen_actor.role,
        )

        resp = client.get(
            "/api/v1/clinician/copilot/patient-summary/citizen-ramesh-patel-01",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert "Operation not permitted for role" in resp.json()["detail"]
