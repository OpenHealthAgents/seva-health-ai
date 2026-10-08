"""Comprehensive Test Suite for SevaHealth Bounded Multi-Agent System.

Validates:
1. Complete contract specifications for all 9 bounded agents:
   - Explicit purpose
   - Allowed tools
   - Input & output schemas
   - Safety constraints
   - Authorization rules
   - Observability
   - Retry policy
   - Timeout
   - Failure behavior
2. Strict non-autonomous enforcement & tool whitelisting
3. Deterministic calculations (scoring, risk models, scheduling)
4. RBAC authorization (citizens cannot invoke clinician/admin agents)
5. Non-diagnostic and non-causal safety boundaries
6. Multi-agent orchestrator pipelines
7. REST API endpoints
"""

import pytest
import asyncio
from starlette.testclient import TestClient

from packages.types.enums import UserRole
from packages.auth.jwt import create_access_token, TokenPayload
from agents.core.models import FailureBehavior, AgentStatus
from agents.core.base import AgentAuthorizationError
from agents.core.tools_registry import DeterministicToolsRegistry, UnauthorizedToolError
from agents.core.telemetry import agent_telemetry_buffer
from agents.registry import agent_registry
from agents.orchestrator import orchestrator
from agents.definitions.screening_agent import ScreeningAgentInput
from agents.definitions.risk_assessment_agent import RiskAssessmentAgentInput
from agents.definitions.trend_analysis_agent import TrendAnalysisAgentInput
from agents.definitions.prevention_agent import PreventionAgentInput
from agents.definitions.health_education_agent import HealthEducationAgentInput
from agents.definitions.followup_agent import FollowUpAgentInput
from agents.definitions.clinical_summary_agent import ClinicalSummaryAgentInput
from agents.definitions.escalation_agent import EscalationAgentInput
from agents.definitions.population_health_agent import PopulationHealthAgentInput
from services.api.main import app

client = TestClient(app)

EXPECTED_9_AGENTS = [
    "ScreeningAgent",
    "RiskAssessmentAgent",
    "TrendAnalysisAgent",
    "PreventionAgent",
    "HealthEducationAgent",
    "FollowUpAgent",
    "ClinicalSummaryAgent",
    "EscalationAgent",
    "PopulationHealthAgent",
]


@pytest.fixture
def citizen_token():
    return TokenPayload(
        sub="cit_test_01",
        tenant_id="karnataka_state_health",
        role=UserRole.CITIZEN,
    )


@pytest.fixture
def health_worker_token():
    return TokenPayload(
        sub="hw_test_01",
        tenant_id="karnataka_state_health",
        role=UserRole.HEALTH_WORKER,
    )


@pytest.fixture
def clinician_token():
    return TokenPayload(
        sub="dr_test_01",
        tenant_id="karnataka_state_health",
        role=UserRole.CLINICIAN,
    )


@pytest.fixture
def admin_token():
    return TokenPayload(
        sub="admin_test_01",
        tenant_id="karnataka_state_health",
        role=UserRole.PUBLIC_HEALTH_ADMIN,
    )


# ==============================================================================
# 1. REGISTRY & CONTRACT SPECIFICATION TESTS (ALL 9 AGENTS)
# ==============================================================================

def test_all_9_agents_registered():
    registered_names = agent_registry.list_agent_names()
    for name in EXPECTED_9_AGENTS:
        assert name in registered_names, f"Missing required agent: {name}"
    assert len(registered_names) == 9


def test_agent_contract_specifications():
    for name in EXPECTED_9_AGENTS:
        agent = agent_registry.get_agent(name)
        meta = agent.get_metadata()

        # 1. Explicit Purpose
        assert meta.purpose is not None and len(meta.purpose) > 20

        # 2. Allowed Tools
        assert isinstance(meta.allowed_tools, list)
        assert len(meta.allowed_tools) >= 1

        # 3. Input & Output Schemas
        assert meta.input_schema_name is not None
        assert meta.output_schema_name is not None

        # 4. Safety Constraints
        assert isinstance(meta.safety_constraints, list)
        assert len(meta.safety_constraints) >= 1

        # 5. Authorization Rules
        assert isinstance(meta.authorized_roles, list)
        assert len(meta.authorized_roles) >= 1

        # 6. Observability & Retry Policy
        assert meta.retry_policy is not None
        assert meta.retry_policy.max_retries >= 1

        # 7. Timeout
        assert meta.timeout_sec > 0.0

        # 8. Failure Behavior
        assert meta.failure_behavior in FailureBehavior

        # 9. Not Autonomous
        assert meta.is_autonomous is False


# ==============================================================================
# 2. TOOL WHITELIST & DETERMINISTIC EXECUTION ENFORCEMENT
# ==============================================================================

@pytest.mark.asyncio
async def test_tool_whitelist_violation_blocked():
    screening_agent = agent_registry.get_agent("ScreeningAgent")
    # ScreeningAgent is only allowed ["calculate_cbac_score", "calculate_idrs_score"]
    # Attempting to call emergency alert tool from screening agent MUST fail
    with pytest.raises(UnauthorizedToolError) as exc_info:
        await screening_agent.invoke_tool("create_emergency_alert", citizen_id="123", urgency="HIGH", reason="test")
    assert "is forbidden from invoking tool" in str(exc_info.value)


@pytest.mark.asyncio
async def test_deterministic_scoring_tools():
    # CBAC Tool
    cbac_res = await DeterministicToolsRegistry.invoke(
        agent_name="ScreeningAgent",
        tool_name="calculate_cbac_score",
        allowed_tools=["calculate_cbac_score"],
        responses={"age_over_30": True, "tobacco_user": True},
    )
    assert cbac_res["score"] >= 2
    assert cbac_res["max_score"] == 10

    # IDRS Tool
    idrs_res = await DeterministicToolsRegistry.invoke(
        agent_name="ScreeningAgent",
        tool_name="calculate_idrs_score",
        allowed_tools=["calculate_idrs_score"],
        age=52,
        waist_circumference_cm=96.0,
        physical_activity="Sedentary",
        family_history_diabetes="Both parents",
    )
    assert idrs_res["score"] >= 60
    assert idrs_res["risk_category"] == "HIGH"


# ==============================================================================
# 3. INDIVIDUAL BOUNDED AGENT EXECUTION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_screening_agent_execution(health_worker_token):
    agent = agent_registry.get_agent("ScreeningAgent")
    input_data = ScreeningAgentInput(
        citizen_id="cit_001",
        age=48,
        waist_circumference_cm=94.0,
        physical_activity_level="Sedentary",
        family_history_diabetes="One parent",
        cbac_answers={"age_over_30": True, "physical_activity_below_150min": True},
    )
    result = await agent.execute(input_data, health_worker_token)
    assert result.success is True
    assert result.data.idrs_score >= 30
    assert result.data.composite_tier in ["MODERATE", "HIGH"]
    assert "Screening complete" in result.data.conversational_summary


@pytest.mark.asyncio
async def test_risk_assessment_agent_execution(citizen_token):
    agent = agent_registry.get_agent("RiskAssessmentAgent")
    input_data = RiskAssessmentAgentInput(
        citizen_id="cit_001",
        vitals={"systolic_bp": 138.0, "fasting_glucose": 118.0, "bmi": 27.2},
    )
    result = await agent.execute(input_data, citizen_token)
    assert result.success is True
    assert result.data.composite_score > 0.0
    assert len(result.data.domains) >= 3
    assert "non-diagnostic" in result.disclaimer.lower()


@pytest.mark.asyncio
async def test_trend_analysis_agent_non_causal_language(citizen_token):
    agent = agent_registry.get_agent("TrendAnalysisAgent")
    input_data = TrendAnalysisAgentInput(citizen_id="cit_001")
    result = await agent.execute(input_data, citizen_token)
    assert result.success is True
    assert result.data.non_causal_language_verified is True
    # Ensure cautious correlation wording rather than direct causal claims
    assert "caused by" not in result.data.narrative_interpretation.lower()


@pytest.mark.asyncio
async def test_prevention_agent_zero_prescribing_boundary(citizen_token):
    agent = agent_registry.get_agent("PreventionAgent")
    input_data = PreventionAgentInput(
        citizen_id="cit_001",
        risk_tier="HIGH",
        identified_risks=["Prediabetes", "Stage 1 HTN"],
    )
    result = await agent.execute(input_data, citizen_token)
    assert result.success is True
    assert result.data.no_medication_disclaimer_confirmed is True
    assert result.data.duration_days == 30
    assert len(result.data.pillar_goals) >= 3


@pytest.mark.asyncio
async def test_health_education_agent_grounded_guidelines(citizen_token):
    agent = agent_registry.get_agent("HealthEducationAgent")
    input_data = HealthEducationAgentInput(topic="diabetes")
    result = await agent.execute(input_data, citizen_token)
    assert result.success is True
    assert len(result.data.evidence_citations) >= 1
    assert "ICMR" in result.data.evidence_citations[0] or "WHO" in result.data.evidence_citations[0]


@pytest.mark.asyncio
async def test_followup_agent_scheduling(health_worker_token):
    agent = agent_registry.get_agent("FollowUpAgent")
    input_data = FollowUpAgentInput(
        citizen_id="cit_001",
        scheduled_days_delay=7,
        preferred_channel="SMS",
    )
    result = await agent.execute(input_data, health_worker_token)
    assert result.success is True
    assert result.data.schedule_status == "SCHEDULED"
    assert "opt-out" in result.data.opt_out_notice.lower()


@pytest.mark.asyncio
async def test_clinical_summary_agent_clinician_only(clinician_token, citizen_token):
    agent = agent_registry.get_agent("ClinicalSummaryAgent")
    input_data = ClinicalSummaryAgentInput(patient_id="cit_001")

    # Clinician is authorized
    result = await agent.execute(input_data, clinician_token)
    assert result.success is True
    assert result.data.clinician_signoff_required is True
    assert "DRAFT" in result.data.draft_status

    # Citizen is FORBIDDEN
    with pytest.raises(AgentAuthorizationError):
        await agent.execute(input_data, citizen_token)


@pytest.mark.asyncio
async def test_escalation_agent_acute_red_flag_detection(citizen_token):
    agent = agent_registry.get_agent("EscalationAgent")

    # Severe chest pain symptom
    red_flag_input = EscalationAgentInput(
        citizen_id="cit_001",
        symptom_text="I have severe crushing chest pain radiating to left arm",
        vitals={"systolic_bp": 140.0},
    )
    result = await agent.execute(red_flag_input, citizen_token)
    assert result.success is True
    assert result.data.is_escalated is True
    assert result.data.urgency_level == "EMERGENT"
    assert "108" in result.data.emergency_instructions

    # Hypertensive crisis (BP >= 180 mmHg)
    htn_crisis_input = EscalationAgentInput(
        citizen_id="cit_001",
        symptom_text="Mild headache",
        vitals={"systolic_bp": 185.0},
    )
    result_htn = await agent.execute(htn_crisis_input, citizen_token)
    assert result_htn.data.is_escalated is True
    assert result_htn.data.urgency_level == "EMERGENT"


@pytest.mark.asyncio
async def test_population_health_agent_privacy_thresholds(admin_token, citizen_token):
    agent = agent_registry.get_agent("PopulationHealthAgent")
    input_data = PopulationHealthAgentInput()

    # Public Health Admin authorized
    result = await agent.execute(input_data, admin_token)
    assert result.success is True
    assert result.data.privacy_threshold_enforced is True
    assert result.data.minimum_cohort_threshold_n >= 10

    # Citizen FORBIDDEN
    with pytest.raises(AgentAuthorizationError):
        await agent.execute(input_data, citizen_token)


# ==============================================================================
# 4. ORCHESTRATION PIPELINES
# ==============================================================================

@pytest.mark.asyncio
async def test_orchestrator_screening_pipeline(health_worker_token):
    res = await orchestrator.run_screening_to_prevention_pipeline(
        citizen_id="cit_pipeline_01",
        age=50,
        gender="MALE",
        waist_cm=95.0,
        activity_level="Sedentary",
        family_history="One parent",
        cbac_answers={"age_over_30": True},
        vitals={"systolic_bp": 138.0, "fasting_glucose": 115.0},
        actor=health_worker_token,
    )
    assert res.pipeline_status == "COMPLETED"
    assert "screening" in res.model_dump()
    assert "risk_assessment" in res.model_dump()
    assert "trajectory" in res.model_dump()
    assert "prevention_plan" in res.model_dump()


@pytest.mark.asyncio
async def test_orchestrator_conversational_check(citizen_token):
    # Emergency message routes to acute escalation
    res = await orchestrator.run_conversational_safety_pipeline(
        citizen_id="cit_001",
        user_message="I have severe chest pain and dizziness",
        actor=citizen_token,
    )
    assert res["is_escalated"] is True
    assert res["route"] == "EMERGENCY_ESCALATION"


# ==============================================================================
# 5. REST API ENDPOINTS
# ==============================================================================

def test_api_list_agents():
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert data["total_agents"] == 9
    assert "ScreeningAgent" in data["agents"]


def test_api_agent_specs():
    response = client.get("/api/v1/agents/specs")
    assert response.status_code == 200
    specs = response.json()
    assert len(specs) == 9
    assert specs[0]["is_autonomous"] is False


def test_api_execute_screening_agent():
    token = create_access_token(
        subject="hw_01",
        tenant_id="karnataka_state_health",
        role=UserRole.HEALTH_WORKER,
    )
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "citizen_id": "cit_001",
        "input_payload": {
            "citizen_id": "cit_001",
            "age": 45,
            "waist_circumference_cm": 92.0,
            "physical_activity_level": "Sedentary",
            "family_history_diabetes": "None",
            "cbac_answers": {},
            "vitals": {},
        }
    }
    response = client.post("/api/v1/agents/ScreeningAgent/execute", json=payload, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["agent_name"] == "ScreeningAgent"
    assert res_data["success"] is True


def test_api_rbac_forbidden_on_clinical_agent():
    citizen_jwt = create_access_token(
        subject="cit_01",
        tenant_id="karnataka_state_health",
        role=UserRole.CITIZEN,
    )
    headers = {"Authorization": f"Bearer {citizen_jwt}"}

    payload = {
        "citizen_id": "cit_01",
        "input_payload": {"patient_id": "cit_01"}
    }
    # Citizen executing ClinicalSummaryAgent must return 403 Forbidden
    response = client.post("/api/v1/agents/ClinicalSummaryAgent/execute", json=payload, headers=headers)
    assert response.status_code == 403
    assert "is not authorized to invoke agent" in response.json()["detail"]


def test_api_telemetry_logs():
    token = create_access_token(
        subject="admin_01",
        tenant_id="karnataka_state_health",
        role=UserRole.SYSTEM_ADMIN,
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/agents/telemetry/logs", headers=headers)
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
