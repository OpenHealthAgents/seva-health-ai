from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import uuid

from packages.clinical_models.risk import RiskAssessment
from packages.clinical_models.triage import ClinicalTriageCase, SOAPReport
from packages.types.enums import RiskTier, TriageUrgency, AuditAction
from packages.auth.jwt import get_current_user_token, TokenPayload
from packages.observability.audit import audit_logger
from services.risk_engine.evaluator import evaluate_ncd_domains
from services.risk_engine.engine import ncd_risk_engine, ModularRiskAssessment
from services.wearable.adapter import wearable_adapter
from services.store import store
import time
from packages.observability.context import SpanStage
from packages.observability.tracer import tracer
from packages.observability.metrics import metrics

router = APIRouter(prefix="/risk", tags=["NCD Risk & Explainability Engine"])


@router.get("/models", response_model=List[Dict[str, Any]])
async def get_registered_risk_models(
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Returns catalog of registered NCD domain risk models, their clinical provenance,
    validation status, input specifications, and limitations.
    """
    return ncd_risk_engine.list_models()


@router.post("/evaluate-modular/{citizen_id}", response_model=ModularRiskAssessment)
async def evaluate_citizen_risk_modular(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Evaluates citizen risk using modular domain models (ICMR-INDIAB, ACC/AHA, WHO-SEAR, etc.)
    with unit normalization and physiological safety boundaries.
    """
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    observations = store.get_citizen_observations(citizen_id)
    screenings = store.get_citizen_screenings(citizen_id)
    latest_screening = screenings[-1] if screenings else None

    idrs = latest_screening.calculated_idrs_score if latest_screening else 40
    smoker = latest_screening.cbac.tobacco_user if (latest_screening and latest_screening.cbac) else False

    # Calculate age safely from birth_date
    citizen_age = 45
    if hasattr(citizen, "birth_date") and citizen.birth_date:
        try:
            b_year = int(str(citizen.birth_date).split("-")[0])
            citizen_age = max(1, datetime.now(timezone.utc).year - b_year)
        except Exception:
            citizen_age = 45

    # Aggregate raw inputs for modular engine
    raw_inputs: Dict[str, Any] = {
        "AGE": citizen_age,
        "SEX": citizen.gender.value if hasattr(citizen.gender, "value") else str(citizen.gender),
        "IDRS_SCORE": idrs,
        "SMOKING": smoker,
    }
    for obs in observations:
        raw_inputs[obs.code] = obs.value

    wearable_proj = wearable_adapter.get_projection(citizen_id)

    modular_result = ncd_risk_engine.evaluate(
        raw_inputs=raw_inputs,
        wearable_projection=wearable_proj,
    )

    audit_logger.record(
        tenant_id=citizen.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.RISK_ASSESSED,
        resource_type="ModularRiskAssessment",
        resource_id=citizen_id,
    )

    return modular_result


@router.post("/evaluate-custom", response_model=ModularRiskAssessment)
async def evaluate_custom_risk_payload(
    payload: Dict[str, Any],
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Direct evaluation of arbitrary screening inputs for clinical what-if simulations,
    point-of-care screening apps, and demographic scenarios.
    """
    return ncd_risk_engine.evaluate(raw_inputs=payload)


@router.post("/evaluate/{citizen_id}", response_model=RiskAssessment)
async def evaluate_citizen_risk(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    observations = store.get_citizen_observations(citizen_id)
    screenings = store.get_citizen_screenings(citizen_id)
    latest_screening = screenings[-1] if screenings else None

    idrs = latest_screening.calculated_idrs_score if latest_screening else 40
    smoker = latest_screening.cbac.tobacco_user if (latest_screening and latest_screening.cbac) else False

    wearable_proj = wearable_adapter.get_projection(citizen_id)

    start_eval = time.time()
    with tracer.span(
        name="EvaluateNCDDomains",
        stage=SpanStage.RISK_ENGINE,
        tags={"citizen_id": citizen_id, "idrs_score": idrs},
    ) as risk_span:
        domains, overall_score, tier, trajectory, drivers, protective = evaluate_ncd_domains(
            observations=observations,
            idrs_score=idrs or 40,
            gender=citizen.gender.value if hasattr(citizen.gender, "value") else str(citizen.gender),
            smoker=smoker,
            wearable_projection=wearable_proj,
        )
        duration_ms = round((time.time() - start_eval) * 1000, 2)
        metrics.record_risk_engine(domain="multidomain", duration_ms=duration_ms, risk_tier=tier.value)
        metrics.record_model_inference(model_version="calibrated_ensemble_v1.0.0", duration_ms=duration_ms)
        risk_span.set_tag("tier", tier.value)
        risk_span.set_tag("overall_score", overall_score)

    assessment = RiskAssessment(
        id=str(uuid.uuid4()),
        tenant_id=citizen.tenant_id,
        citizen_id=citizen_id,
        screening_session_id=latest_screening.id if latest_screening else None,
        overall_score=overall_score,
        overall_tier=tier,
        domains=domains,
        trajectory=trajectory,
        confidence_score=0.92 if observations else 0.65,
        top_drivers=drivers,
        protective_factors=protective,
        clinical_summary=(
            f"Citizen exhibits {tier.value} NCD risk ({overall_score*100:.0f}% composite index). "
            f"Top driving factor is {drivers[0].feature_name if drivers else 'general lifestyle factors'}. "
            f"Longitudinal trajectory is {trajectory.value}."
        ),
        evaluated_at=datetime.now(timezone.utc),
    )

    with tracer.span(
        name="StoreRiskAssessment",
        stage=SpanStage.CLINICAL_REPOSITORY,
        tags={"table": "risk_assessments", "citizen_id": citizen_id},
    ):
        store.add_risk_assessment(assessment)
        metrics.record_db_query(operation="INSERT", table="risk_assessments", duration_ms=2.1, success=True)

    # Automatic Clinical Triage Escalation for HIGH or CRITICAL tiers
    if tier in [RiskTier.HIGH, RiskTier.CRITICAL]:
        urgency = TriageUrgency.EMERGENT if tier == RiskTier.CRITICAL else TriageUrgency.PRIORITY
        triage_case = ClinicalTriageCase(
            id=str(uuid.uuid4()),
            tenant_id=citizen.tenant_id,
            citizen_id=citizen.id,
            citizen_name=f"{citizen.first_name} {citizen.last_name}",
            risk_assessment_id=assessment.id,
            urgency=urgency,
            escalation_reason=f"Elevated NCD risk tier ({tier.value}) with {assessment.top_drivers[0].feature_name if assessment.top_drivers else 'high risk drivers'}",
            soap_note=SOAPReport(
                subjective=f"Patient {citizen.first_name} presents with {trajectory.value} lifestyle risk. Reports screening via {latest_screening.conducted_at.strftime('%Y-%m-%d') if latest_screening else 'field camp'}.",
                objective=f"Composite Risk: {overall_score*100:.0f}%. Key drivers: {', '.join([d.feature_name for d in drivers[:2]]) if drivers else 'N/A'}.",
                assessment=f"Clinical decision support flags {tier.value} risk of metabolic and vascular progression. Clinical review recommended.",
                plan="1. Review baseline vitals. 2. Verify 30-day preventive intervention care plan. 3. Schedule follow-up / tele-consult.",
            ),
        )
        store.add_triage_case(triage_case)

    audit_logger.record(
        tenant_id=citizen.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.RISK_ASSESSED,
        resource_type="RiskAssessment",
        resource_id=assessment.id,
    )

    return assessment


@router.get("/latest/{citizen_id}", response_model=RiskAssessment)
async def get_latest_citizen_risk(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    risk = store.get_latest_risk(citizen_id)
    if not risk:
        # Trigger on-the-fly evaluation if not present
        return await evaluate_citizen_risk(citizen_id, current_user)
    return risk
