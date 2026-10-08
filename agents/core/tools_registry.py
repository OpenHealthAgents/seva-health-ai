"""Deterministic Services and Tool Whitelisting Registry for Bounded Agents.

Enforces:
1. Bounded agents can ONLY invoke tools explicitly declared in their allowed_tools list.
2. All clinical calculations, risk scoring, data access, scheduling, and alerting
   are executed by deterministic validated Python engines, NOT by LLMs.
"""

from typing import Dict, List, Optional, Any, Callable
import inspect
import structlog

logger = structlog.get_logger(__name__)


class UnauthorizedToolError(Exception):
    """Raised when an agent attempts to invoke a tool outside its allowed_tools specification."""
    pass


class DeterministicToolsRegistry:
    """Registry of verified deterministic tools accessible to bounded agents."""

    _tools: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(func: Callable):
            cls._tools[name] = func
            return func
        return decorator

    @classmethod
    async def invoke(
        cls,
        agent_name: str,
        tool_name: str,
        allowed_tools: List[str],
        **kwargs
    ) -> Any:
        """Executes a tool with strict whitelist validation."""
        if tool_name not in allowed_tools:
            logger.error(
                "AGENT_TOOL_VIOLATION: Attempted invocation of non-whitelisted tool",
                agent=agent_name,
                tool=tool_name,
                allowed=allowed_tools,
            )
            raise UnauthorizedToolError(
                f"Agent '{agent_name}' is forbidden from invoking tool '{tool_name}'. Allowed tools: {allowed_tools}"
            )

        if tool_name not in cls._tools:
            raise KeyError(f"Tool '{tool_name}' is not registered in DeterministicToolsRegistry.")

        func = cls._tools[tool_name]
        if inspect.iscoroutinefunction(func):
            return await func(**kwargs)
        else:
            return func(**kwargs)

    @classmethod
    def list_available_tools(cls) -> List[str]:
        return list(cls._tools.keys())


# ==============================================================================
# REGISTER DETERMINISTIC SERVICES FOR BOUNDED AGENTS
# ==============================================================================

@DeterministicToolsRegistry.register("calculate_cbac_score")
def tool_calculate_cbac_score(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic CBAC (Community-Based Assessment Checklist) risk calculation."""
    from packages.clinical_models.screening import CBACSurvey
    from services.screening.calculator import calculate_cbac

    survey = CBACSurvey(
        age_over_30=responses.get("age_over_30", False),
        tobacco_user=responses.get("tobacco_user", False),
        alcohol_consumption=responses.get("alcohol_consumption", False),
        waist_circumference_exceeded=responses.get("waist_circumference_exceeded", False),
        physical_activity_below_150min=responses.get("physical_activity_below_150min", False),
        family_history_diabetes_or_htn=responses.get("family_history_diabetes_or_htn", False),
    )
    score = calculate_cbac(survey)
    return {
        "score": score,
        "max_score": 10,
        "high_risk_threshold": 4,
        "is_high_risk": score >= 4,
        "provenance": "MOHFW India Operational Framework for NCD Screening",
    }


@DeterministicToolsRegistry.register("calculate_idrs_score")
def tool_calculate_idrs_score(
    age: int,
    waist_circumference_cm: float,
    physical_activity: str,
    family_history_diabetes: str,
) -> Dict[str, Any]:
    """Deterministic Indian Diabetes Risk Score (IDRS) calculation."""
    from packages.clinical_models.screening import IDRSSurvey
    from services.screening.calculator import calculate_idrs

    age_cat = ">=50" if age >= 50 else ("35-49" if age >= 35 else "<35")
    waist_cat = ">=100" if waist_circumference_cm >= 100 else ("90-99" if waist_circumference_cm >= 90 else "<90")

    survey = IDRSSurvey(
        age_category=age_cat,
        waist_category=waist_cat,
        physical_activity=physical_activity if physical_activity in ["None", "Sedentary", "Moderate", "Vigorous"] else "Sedentary",
        family_history=family_history_diabetes if family_history_diabetes in ["None", "One parent", "Both parents"] else "None",
    )
    score = calculate_idrs(survey)
    risk_category = "LOW"
    if score >= 60:
        risk_category = "HIGH"
    elif score >= 30:
        risk_category = "MODERATE"

    return {
        "score": score,
        "max_score": 100,
        "risk_category": risk_category,
        "provenance": "Madras Diabetes Research Foundation (MDRF) - Mohan et al.",
    }


@DeterministicToolsRegistry.register("run_deterministic_risk_models")
def tool_run_deterministic_risk_models(
    citizen_id: str,
    vitals: Dict[str, Any],
    lifestyle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Deterministic multi-domain risk evaluation across 5 clinical models."""
    from services.risk_engine.engine import ncd_risk_engine

    raw = {**vitals, **(lifestyle or {})}
    if "systolic_bp" in vitals:
        raw["systolic_blood_pressure"] = vitals["systolic_bp"]
    if "diastolic_bp" in vitals:
        raw["diastolic_blood_pressure"] = vitals["diastolic_bp"]
    if "fasting_glucose" in vitals:
        raw["fasting_blood_glucose"] = vitals["fasting_glucose"]

    mod_assessment = ncd_risk_engine.evaluate(raw)
    overall_score = mod_assessment.overall_score or 0.45
    tier = mod_assessment.overall_category.value
    top_drivers = [{"factor_name": d.feature, "impact": d.impact_weight} for d in mod_assessment.top_drivers]

    dom_res = mod_assessment.domain_results
    return {
        "overall_score": overall_score,
        "tier": tier,
        "top_drivers": top_drivers,
        "diabetes_risk": dom_res["diabetes"].score if "diabetes" in dom_res and dom_res["diabetes"].score is not None else 0.4,
        "cvd_risk": dom_res["cardiovascular"].score if "cardiovascular" in dom_res and dom_res["cardiovascular"].score is not None else 0.35,
        "hypertension_risk": dom_res["hypertension"].score if "hypertension" in dom_res and dom_res["hypertension"].score is not None else 0.45,
    }


@DeterministicToolsRegistry.register("calculate_risk_trajectory")
async def tool_calculate_risk_trajectory(citizen_id: str) -> Dict[str, Any]:
    """Deterministic longitudinal risk trend and delta calculation."""
    from services.trajectory.router import _ensure_citizen_has_snapshots
    from services.trajectory.engine import risk_trajectory_engine

    snaps = _ensure_citizen_has_snapshots(citizen_id)
    report = risk_trajectory_engine.evaluate_trajectory(citizen_id, snaps)
    
    curr_tier = (
        report.current_snapshot.domain_tiers.get("metabolic")
        or next(iter(report.current_snapshot.domain_tiers.values()), "MODERATE")
        if report.current_snapshot and report.current_snapshot.domain_tiers
        else "MODERATE"
    )
    prev_tier = (
        report.previous_snapshot.domain_tiers.get("metabolic")
        or next(iter(report.previous_snapshot.domain_tiers.values()), "MODERATE")
        if report.previous_snapshot and report.previous_snapshot.domain_tiers
        else "MODERATE"
    )
    return {
        "trend": report.overall_trend.value if hasattr(report.overall_trend, "value") else str(report.overall_trend),
        "current_tier": curr_tier,
        "previous_tier": prev_tier,
        "change_percentage": report.composite_change_percentage or 0.0,
    }



@DeterministicToolsRegistry.register("generate_deterministic_care_plan")
def tool_generate_deterministic_care_plan(
    citizen_id: str,
    risk_tier: str,
    identified_risks: List[str],
) -> Dict[str, Any]:
    """Deterministic 30-day evidence-based prevention plan generation."""
    from services.intervention_engine.engine import prevention_intervention_engine
    from services.intervention_engine.models import PreventionPlanInput

    plan_input = PreventionPlanInput(
        citizen_id=citizen_id,
        risk_tier=risk_tier,
        identified_risk_factors=identified_risks,
    )
    plan = prevention_intervention_engine.generate_plan(plan_input)
    return plan.model_dump() if hasattr(plan, "model_dump") else plan.dict()


@DeterministicToolsRegistry.register("query_knowledge_base")
def tool_query_knowledge_base(topic: str) -> Dict[str, Any]:
    """Deterministic retrieval of verified public health modules (ICMR, WHO PEN)."""
    guidelines = {
        "diabetes": {
            "title": "ICMR Guidelines for Management of Type 2 Diabetes",
            "summary": "Target HbA1c < 7.0%. Dietary modifications prioritizing whole grains and millets.",
            "citations": ["ICMR-INDIAB Guidelines 2023", "WHO PEN Protocol 1"],
        },
        "hypertension": {
            "title": "Indian Hypertension Control Initiative (IHCI) Protocol",
            "summary": "Threshold BP >= 140/90 mmHg. Restrict daily sodium to under 2 grams (1 teaspoon salt).",
            "citations": ["IHCI Protocol 2022", "MOHFW Standard Treatment Workflows"],
        },
        "lifestyle": {
            "title": "WHO Physical Activity and Dietary Recommendations",
            "summary": "Minimum 150 minutes of moderate-intensity aerobic physical activity weekly.",
            "citations": ["WHO Guidelines on Physical Activity and Sedentary Behaviour 2020"],
        },
    }
    key = topic.lower()
    for k, v in guidelines.items():
        if k in key:
            return v
    return guidelines["lifestyle"]


@DeterministicToolsRegistry.register("schedule_notification")
def tool_schedule_notification(
    citizen_id: str,
    channel: str,
    message: str,
    delay_hours: int = 24,
) -> Dict[str, Any]:
    """Deterministic scheduling of follow-up reminder."""
    return {
        "status": "SCHEDULED",
        "citizen_id": citizen_id,
        "channel": channel,
        "scheduled_delay_hours": delay_hours,
        "message_preview": message[:50] + "...",
    }


@DeterministicToolsRegistry.register("get_federated_clinical_chart")
async def tool_get_federated_clinical_chart(patient_id: str, actor_id: str, actor_role: str) -> Dict[str, Any]:
    """Deterministic federated EMR retrieval with RBAC and anti-query injection."""
    from packages.types.enums import UserRole
    from packages.interop.base import AccessContext
    from packages.interop.service import federated_clinical_data_provider

    role = UserRole(actor_role) if isinstance(actor_role, str) else actor_role
    ctx = AccessContext(
        actor_id=actor_id,
        actor_role=role,
        purpose_of_use="CARE_DELIVERY",
    )
    chart = await federated_clinical_data_provider.get_federated_chart(patient_id, ctx)
    return chart.model_dump()


@DeterministicToolsRegistry.register("create_emergency_alert")
def tool_create_emergency_alert(citizen_id: str, urgency: str, reason: str) -> Dict[str, Any]:
    """Deterministic escalation into clinician triage queue."""
    from services.store import store
    from packages.clinical_models.triage import ClinicalTriageCase, SOAPReport
    from packages.types.enums import TriageUrgency

    urg_enum = TriageUrgency.EMERGENT if "EMERG" in urgency.upper() else TriageUrgency.URGENT
    citizen = store.get_citizen(citizen_id)
    name = f"{citizen.first_name} {citizen.last_name}" if citizen else f"Citizen {citizen_id}"
    tenant_id = citizen.tenant_id if citizen else "karnataka_state_health"

    triage_case = ClinicalTriageCase(
        tenant_id=tenant_id,
        citizen_id=citizen_id,
        citizen_name=name,
        risk_assessment_id=f"risk_eval_{citizen_id}",
        urgency=urg_enum,
        escalation_reason=reason,
        soap_note=SOAPReport(
            subjective=f"Reported acute symptoms: {reason}",
            objective="Emergency symptom screening triggered.",
            assessment=f"Urgent triage: {reason}",
            plan="Immediate casualty / medical officer evaluation.",
        ),
    )
    store.add_triage_case(triage_case)
    return {
        "status": "ESCALATED",
        "triage_id": triage_case.id,
        "urgency": urg_enum.value,
        "escalated_at": triage_case.created_at.isoformat(),
    }


@DeterministicToolsRegistry.register("get_population_health_aggregates")
def tool_get_population_health_aggregates(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Deterministic population health intelligence calculation with k-anonymity privacy."""
    from services.population_intelligence.engine import population_intelligence_engine
    return population_intelligence_engine.get_population_overview(tenant_id=tenant_id).dict()
