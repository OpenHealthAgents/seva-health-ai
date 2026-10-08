from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone

from packages.clinical_models.care_plan import CarePlan
from packages.auth.jwt import get_current_user_token, TokenPayload
from packages.types.enums import AuditAction
from packages.observability.audit import audit_logger
from services.intervention_engine.generator import generate_30_day_care_plan
from services.intervention_engine.models import (
    ComprehensivePreventionPlan,
    PreventionPlanInput,
)
from services.intervention_engine.engine import prevention_intervention_engine
from services.intervention_engine.rules import rule_registry, InterventionRule
from services.intervention_engine.templates import PREVENTION_TEMPLATES, PreventionTemplate
from services.risk_engine.evaluator import evaluate_ncd_domains
from services.store import store

router = APIRouter(prefix="/intervention", tags=["Preventive Interventions"])


@router.get("/templates", response_model=List[PreventionTemplate])
async def list_prevention_templates(
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Lists available evidence-based 30-day prevention journey templates."""
    return list(PREVENTION_TEMPLATES.values())


@router.get("/rules", response_model=List[InterventionRule])
async def list_configurable_rules(
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Lists active configurable intervention rules and their prioritization rankings."""
    return rule_registry.list_rules()


@router.post("/generate-comprehensive/{citizen_id}", response_model=ComprehensivePreventionPlan)
async def generate_comprehensive_prevention_plan(
    citizen_id: str,
    custom_input: Optional[PreventionPlanInput] = None,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Generates a complete 30-day prevention care plan including:
    - Goals (SMART preventive targets)
    - Actions (Prioritized: Safety > Evidence > Benefit > Feasibility > Preference)
    - Daily Tasks (30-day interactive checklist)
    - Reminders (Scheduled notifications across channels)
    - Educational Content (Culturally adapted evidence modules)
    - Measurements (Biometric tracking schedule)
    - Follow-Up Schedule (ASHA, Nurse, Clinician checkpoints)
    """
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    risk = store.get_latest_risk(citizen_id)
    trajectory_snapshots = store.get_trajectory_snapshots(citizen_id)
    latest_traj = "STABLE"
    if risk and hasattr(risk.trajectory, "value"):
        latest_traj = risk.trajectory.value

    # Prepare input payload
    if custom_input:
        plan_input = custom_input
        plan_input.citizen_id = citizen_id
        plan_input.tenant_id = citizen.tenant_id
        if not plan_input.risk_profile and risk:
            plan_input.risk_profile = {
                "overall_tier": risk.overall_tier.value,
                "overall_score": risk.overall_score,
                "domains": {
                    "diabetes_risk": risk.domains.diabetes_risk,
                    "hypertension_risk": risk.domains.hypertension_risk,
                    "cardiovascular_risk": risk.domains.cardiovascular_risk,
                    "metabolic_syndrome_risk": risk.domains.metabolic_syndrome_risk,
                    "ckd_risk": risk.domains.ckd_risk,
                }
            }
        if not plan_input.risk_trajectory:
            plan_input.risk_trajectory = latest_traj
    else:
        # Build from recorded citizen profile & risk
        domains_dict = {}
        if risk:
            domains_dict = {
                "diabetes_risk": risk.domains.diabetes_risk,
                "hypertension_risk": risk.domains.hypertension_risk,
                "cardiovascular_risk": risk.domains.cardiovascular_risk,
                "metabolic_syndrome_risk": risk.domains.metabolic_syndrome_risk,
                "ckd_risk": risk.domains.ckd_risk,
            }
        plan_input = PreventionPlanInput(
            citizen_id=citizen_id,
            tenant_id=citizen.tenant_id,
            risk_profile={
                "overall_tier": risk.overall_tier.value if risk else "MODERATE",
                "overall_score": risk.overall_score if risk else 0.40,
                "domains": domains_dict,
            },
            risk_trajectory=latest_traj,
            lifestyle={},
            goals=["Improve glycemic stability", "Walk 8,000 steps daily"],
            preferences={"dietary_pattern": "VEGETARIAN", "exercise_type": "WALKING"},
            constraints=[],
            available_community_resources=[
                {"name": "Ward 12 Community Park", "type": "WALKING_TRACK"},
                {"name": "Devanahalli PHC Yoga Center", "type": "YOGA_WELLNESS"},
            ],
            clinician_recommendations=[],
        )

    # Synthesize comprehensive plan
    plan = prevention_intervention_engine.generate_plan(plan_input)
    store.set_comprehensive_plan(plan)

    # Also sync backward-compatible CarePlan into store
    backward_care_plan = generate_30_day_care_plan(
        citizen_id=citizen_id,
        tenant_id=citizen.tenant_id,
        risk=risk if risk else store.get_latest_risk(citizen_id),
    )
    store.set_care_plan(backward_care_plan)

    audit_logger.record(
        tenant_id=citizen.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.CARE_PLAN_GENERATED,
        resource_type="ComprehensivePreventionPlan",
        resource_id=plan.id,
    )

    return plan


@router.get("/comprehensive/{citizen_id}", response_model=ComprehensivePreventionPlan)
async def get_comprehensive_prevention_plan(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Retrieves the active 30-day comprehensive prevention plan for a citizen."""
    plan = store.get_comprehensive_plan(citizen_id)
    if not plan:
        return await generate_comprehensive_prevention_plan(citizen_id, None, current_user)
    return plan


# =========================================================================
# BACKWARD COMPATIBILITY ENDPOINTS (Preserved for existing frontend/tests)
# =========================================================================

@router.post("/generate/{citizen_id}", response_model=CarePlan)
async def generate_citizen_care_plan(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    risk = store.get_latest_risk(citizen_id)
    if not risk:
        # Evaluate risk if not yet run
        obs = store.get_citizen_observations(citizen_id)
        domains, score, tier, traj, drivers, prot = evaluate_ncd_domains(obs, gender=citizen.gender.value)
        from packages.clinical_models.risk import RiskAssessment
        import uuid
        risk = RiskAssessment(
            id=str(uuid.uuid4()),
            tenant_id=citizen.tenant_id,
            citizen_id=citizen_id,
            overall_score=score,
            overall_tier=tier,
            domains=domains,
            trajectory=traj,
            confidence_score=0.85,
            top_drivers=drivers,
            protective_factors=prot,
            clinical_summary="Auto-evaluated for care plan generation.",
        )
        store.add_risk_assessment(risk)

    plan = generate_30_day_care_plan(
        citizen_id=citizen_id,
        tenant_id=citizen.tenant_id,
        risk=risk,
    )
    store.set_care_plan(plan)

    audit_logger.record(
        tenant_id=citizen.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.CARE_PLAN_GENERATED,
        resource_type="CarePlan",
        resource_id=plan.id,
    )
    return plan


@router.get("/plan/{citizen_id}", response_model=CarePlan)
async def get_citizen_care_plan(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    plan = store.get_care_plan(citizen_id)
    if not plan:
        return await generate_citizen_care_plan(citizen_id, current_user)
    return plan


@router.post("/tasks/{citizen_id}/{task_id}/toggle", response_model=CarePlan)
async def toggle_task_completion(
    citizen_id: str,
    task_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    plan = store.get_care_plan(citizen_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Care plan not found")

    target_task = next((t for t in plan.daily_tasks if t.id == task_id), None)
    if not target_task:
        raise HTTPException(status_code=404, detail="Task not found")

    target_task.completed = not target_task.completed
    target_task.completed_at = datetime.now(timezone.utc) if target_task.completed else None

    # Recalculate adherence percentage
    completed_count = sum(1 for t in plan.daily_tasks if t.completed)
    plan.adherence_percentage = round((completed_count / len(plan.daily_tasks)) * 100, 1)

    store.set_care_plan(plan)

    audit_logger.record(
        tenant_id=plan.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.TASK_COMPLETED if target_task.completed else AuditAction.CARE_PLAN_GENERATED,
        resource_type="DailyTask",
        resource_id=task_id,
    )

    return plan
