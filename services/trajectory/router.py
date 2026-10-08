from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone

from packages.auth.jwt import get_current_user_token, TokenPayload
from packages.observability.audit import audit_logger
from packages.types.enums import AuditAction
from services.store import store
from services.trajectory.models import (
    CitizenTrajectoryReport,
    DomainTrajectoryComparison,
    RiskSnapshot,
    TrajectoryDomain,
)
from services.trajectory.engine import risk_trajectory_engine

router = APIRouter(prefix="/trajectory", tags=["Longitudinal Risk Trajectory Engine"])


def _ensure_citizen_has_snapshots(citizen_id: str) -> List[RiskSnapshot]:
    """Retrieves existing snapshots or derives an initial baseline from recorded observations."""
    snaps = store.get_trajectory_snapshots(citizen_id)
    if snaps:
        return snaps

    citizen = store.get_citizen(citizen_id)
    if not citizen:
        return []

    # If no explicit snapshots exist, construct baseline & current from observations
    observations = store.get_citizen_observations(citizen_id)
    obs_map = {o.code: o.value for o in observations}

    # Generate an initial current snapshot
    sbp = obs_map.get("SYSTOLIC_BP", 125.0)
    dbp = obs_map.get("DIASTOLIC_BP", 82.0)
    fbg = obs_map.get("FASTING_GLUCOSE", 100.0)
    hba1c = obs_map.get("HBA1C", 5.6)
    bmi = obs_map.get("BMI", 24.0)
    waist = obs_map.get("WAIST_CIRCUMFERENCE", 88.0)
    chol = obs_map.get("TOTAL_CHOLESTEROL", 190.0)
    tg = obs_map.get("TRIGLYCERIDES", 150.0)
    egfr = obs_map.get("EGFR", 90.0)

    curr_snap = RiskSnapshot(
        citizen_id=citizen_id,
        timestamp=datetime.now(timezone.utc),
        domain_scores={
            "diabetes": 0.65 if (hba1c >= 5.7 or fbg >= 100) else 0.15,
            "hypertension": 0.60 if (sbp >= 130 or dbp >= 85) else 0.12,
            "cardiovascular": 0.42 if (sbp >= 135 or chol >= 200) else 0.18,
            "metabolic": 0.55 if (waist >= 90 or tg >= 150) else 0.20,
            "obesity": 0.58 if (bmi >= 25.0 or waist >= 90) else 0.18,
            "renal": 0.45 if egfr < 90 else 0.12,
            "lifestyle": 0.40,
        },
        domain_tiers={
            "diabetes": "MODERATE" if (hba1c >= 5.7 or fbg >= 100) else "LOW",
            "hypertension": "MODERATE" if (sbp >= 130 or dbp >= 85) else "LOW",
            "cardiovascular": "MODERATE" if (sbp >= 135 or chol >= 200) else "LOW",
            "metabolic": "MODERATE" if (waist >= 90 or tg >= 150) else "LOW",
            "obesity": "HIGH" if (bmi >= 25.0 and waist >= 90) else "MODERATE",
            "renal": "MODERATE" if egfr < 90 else "LOW",
            "lifestyle": "MODERATE",
        },
        key_biomarkers={
            "SYSTOLIC_BP": sbp,
            "DIASTOLIC_BP": dbp,
            "FASTING_GLUCOSE": fbg,
            "HBA1C": hba1c,
            "BMI": bmi,
            "WAIST_CIRCUMFERENCE": waist,
            "TOTAL_CHOLESTEROL": chol,
            "TRIGLYCERIDES": tg,
            "EGFR": egfr,
            "STEPS": 6500,
            "HRV": 42.0,
        },
        source="OBSERVATIONS_DERIVED",
        data_completeness=1.0,
        confidence=0.90,
    )

    store.add_trajectory_snapshot(citizen_id, curr_snap)
    return [curr_snap]


@router.get("/{citizen_id}", response_model=CitizenTrajectoryReport)
async def get_citizen_trajectory_report(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Returns the full multi-domain longitudinal risk trajectory report comparing
    Current vs Previous vs Baseline risk across all 7 clinical domains.
    """
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    snapshots = _ensure_citizen_has_snapshots(citizen_id)
    report = risk_trajectory_engine.evaluate_trajectory(citizen_id, snapshots)

    audit_logger.record(
        tenant_id=citizen.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.RISK_ASSESSED,
        resource_type="CitizenTrajectoryReport",
        resource_id=citizen_id,
    )

    return report


@router.get("/{citizen_id}/domain/{domain_name}", response_model=DomainTrajectoryComparison)
async def get_domain_trajectory(
    citizen_id: str,
    domain_name: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Returns detailed longitudinal trend, percentage change, and contributing factors
    for a specific domain (metabolic, diabetes, hypertension, cardiovascular, obesity, renal, lifestyle).
    """
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    domain_key = domain_name.lower().strip()
    valid_domains = [d.value for d in TrajectoryDomain]
    if domain_key not in valid_domains:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid domain '{domain_name}'. Valid domains: {', '.join(valid_domains)}"
        )

    snapshots = _ensure_citizen_has_snapshots(citizen_id)
    report = risk_trajectory_engine.evaluate_trajectory(citizen_id, snapshots)
    comparison = report.domain_trajectories.get(domain_key)

    if not comparison:
        raise HTTPException(status_code=404, detail=f"Trajectory for domain '{domain_name}' not available")

    return comparison


@router.post("/{citizen_id}/snapshot", response_model=CitizenTrajectoryReport)
async def record_trajectory_snapshot(
    citizen_id: str,
    snapshot: RiskSnapshot,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Records a new point-in-time risk snapshot for the citizen's longitudinal history
    and recalculates updated trajectory trends.
    """
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    # Enforce correct citizen_id
    snapshot.citizen_id = citizen_id
    store.add_trajectory_snapshot(citizen_id, snapshot)

    snapshots = store.get_trajectory_snapshots(citizen_id)
    updated_report = risk_trajectory_engine.evaluate_trajectory(citizen_id, snapshots)

    return updated_report


@router.get("/{citizen_id}/visual", response_class=HTMLResponse)
async def get_visual_trajectory_html(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Renders a standalone interactive HTML visual trajectory widget using Tailwind CSS
    and semantic theme tokens per generative_ui guidelines.
    """
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    snapshots = _ensure_citizen_has_snapshots(citizen_id)
    report = risk_trajectory_engine.evaluate_trajectory(citizen_id, snapshots)
    full_name = f"{citizen.first_name} {citizen.last_name}"

    html_content = risk_trajectory_engine.generate_visual_html(report, full_name)
    return HTMLResponse(content=html_content, status_code=200)


@router.get("/{citizen_id}/svg")
async def get_visual_trajectory_svg(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Returns a standalone SVG vector trajectory graphic for embedding in reports or EMRs."""
    citizen = store.get_citizen(citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    snapshots = _ensure_citizen_has_snapshots(citizen_id)
    report = risk_trajectory_engine.evaluate_trajectory(citizen_id, snapshots)
    svg_content = risk_trajectory_engine.generate_visual_svg(report)

    return Response(content=svg_content, media_type="image/svg+xml")
