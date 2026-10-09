"""FastAPI Router for SevaHealth AI Demo Mode.

Provides dedicated endpoints for innovation challenge judges, clinicians,
and administrators to explore synthetic personas and trigger the interactive
Hero Journey story workflow.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field

from packages.auth.jwt import get_current_user_token, TokenPayload
from packages.types.enums import UserRole
from services.demo.personas import (
    SYNTHETIC_PERSONAS,
    seed_all_synthetic_personas,
    get_persona_summary_list,
    PersonaMetadata,
)
from services.demo.story_runner import (
    execute_demo_story,
    DemoStoryResult,
)
from services.store import store

router = APIRouter(prefix="/demo", tags=["Demo Mode"])

# In-memory cache of latest story run
_latest_story_result: Optional[DemoStoryResult] = None


class RunStoryRequest(BaseModel):
    citizen_id: str = Field(
        default="citizen-arjun-mehta-11",
        description="Persona ID to use as the hero of the narrative",
    )
    clinician_id: str = Field(
        default="doctor-user-01",
        description="Clinician user ID for human-in-the-loop review",
    )


class SeedResponse(BaseModel):
    message: str
    total_personas_seeded: int
    personas: List[PersonaMetadata]


@router.post("/seed", response_model=SeedResponse, status_code=status.HTTP_201_CREATED)
async def seed_demo_environment():
    """Seeds or resets the demo environment with all 12 comprehensive synthetic personas.

    Generates labs, vitals, wearables, screenings, risk scores, trajectories,
    interventions, check-ins, alerts, and referrals for each persona.
    """
    personas_dict = seed_all_synthetic_personas()
    return SeedResponse(
        message="Demo environment successfully populated with 12 diverse clinical personas.",
        total_personas_seeded=len(personas_dict),
        personas=list(personas_dict.values()),
    )


@router.get("/personas", response_model=List[PersonaMetadata])
async def list_demo_personas():
    """Lists all available synthetic personas representing the 10+ core epidemiological phenotypes."""
    if not SYNTHETIC_PERSONAS:
        seed_all_synthetic_personas()
    return list(SYNTHETIC_PERSONAS.values())


@router.get("/personas/{persona_id}", response_model=Dict[str, Any])
async def get_demo_persona_detail(persona_id: str):
    """Retrieves deep clinical record details for a specific synthetic persona."""
    if not SYNTHETIC_PERSONAS:
        seed_all_synthetic_personas()

    if persona_id not in SYNTHETIC_PERSONAS:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")

    meta = SYNTHETIC_PERSONAS[persona_id]
    citizen = store.get_citizen(persona_id)
    observations = store.get_citizen_observations(persona_id)
    risk = store.get_latest_risk(persona_id)
    plan = store.get_care_plan(persona_id)
    snapshots = store.get_trajectory_snapshots(persona_id)
    alerts = store.get_alerts(persona_id)
    referrals = store.get_referrals(persona_id)
    checkins = store.get_checkins(persona_id)
    wearable = store.wearable_data.get(persona_id, [])

    return {
        "metadata": meta.model_dump(),
        "citizen_record": citizen.to_dict() if citizen else None,
        "observations_count": len(observations),
        "latest_risk": risk.model_dump() if risk else None,
        "care_plan": plan.model_dump() if plan else None,
        "trajectory_snapshots_count": len(snapshots),
        "alerts_count": len(alerts),
        "alerts": alerts,
        "referrals_count": len(referrals),
        "referrals": referrals,
        "checkins_count": len(checkins),
        "wearable_records_count": len(wearable),
    }


@router.post("/run-story", response_model=DemoStoryResult)
async def run_demo_story(request: RunStoryRequest = RunStoryRequest()):
    """Executes the complete 9-stage SevaHealth Hero Journey narrative in under 5 seconds:

    1. Moderate Risk Baseline
    2. Silent Progression (Weight ↑, Activity ↓, BP ↑, HbA1c ↑)
    3. Trajectory Detection (Worsening Trajectory Detected)
    4. AI Explains Contributors (Waterfall Decomposition)
    5. AI Creates 30-Day Multi-Pillar Prevention Plan
    6. Citizen Completes Intervention (Adherence 86.7%, Steps ↑)
    7. Risk Reversal (Risk 71% -> 24%, Trajectory turns IMPROVING)
    8. Clinician Reviews & Approves (SOAP Note Sign-Off)
    9. Population Health Dashboard Reflects Outcome
    """
    global _latest_story_result
    result = execute_demo_story(
        citizen_id=request.citizen_id,
        clinician_id=request.clinician_id,
    )
    _latest_story_result = result
    return result


@router.get("/story-status", response_model=Dict[str, Any])
async def get_story_status():
    """Retrieves the latest execution summary of the demo story."""
    if _latest_story_result is None:
        return {
            "status": "NOT_EXECUTED",
            "message": "Demo story has not been executed yet. Call POST /api/v1/demo/run-story to trigger.",
        }
    return {
        "status": "COMPLETED",
        "citizen_id": _latest_story_result.citizen_id,
        "citizen_name": _latest_story_result.citizen_name,
        "total_execution_seconds": _latest_story_result.total_execution_seconds,
        "net_risk_reduction_percentage": _latest_story_result.net_risk_reduction_percentage,
        "clinician_review_status": _latest_story_result.clinician_review_status,
        "stages_count": _latest_story_result.total_stages,
    }


# =============================================================================
# PROMPT 25: SEVA INNOVATION CHALLENGE DEMO WORKFLOW (STEPS 1 - 16)
# =============================================================================

from services.demo.challenge_workflow import (
    execute_challenge_step,
    execute_all_challenge_steps,
    reset_challenge_demo,
    get_challenge_demo_state,
    ChallengeStepRecord,
    ChallengeWorkflowSummary,
)

challenge_router = APIRouter(prefix="/challenge-demo", tags=["Challenge Demo Workflow"])


@router.post("/challenge/reset", response_model=Dict[str, Any])
@challenge_router.post("/reset", response_model=Dict[str, Any])
async def reset_challenge_demo_endpoint():
    """DEMO RESET BUTTON: Purges all challenge artifacts and restores clean baseline.

    Resets citizen Devendra Sharma, vitals, trajectories, care plans, alerts, and triage cases.
    Ensures that the 16-step demonstration works reliably and deterministically every time.
    """
    return reset_challenge_demo()


@router.post("/challenge/run", response_model=ChallengeWorkflowSummary)
@challenge_router.post("/run", response_model=ChallengeWorkflowSummary)
async def run_all_challenge_steps_endpoint():
    """Executes all 16 steps of the Seva Innovation Challenge Demo:

    STEP 1: Health worker registers citizen.
    STEP 2: Citizen completes NCD screening.
    STEP 3: System calculates risk.
    STEP 4: AI explains risk.
    STEP 5: System generates personalized prevention plan.
    STEP 6: Citizen connects wearable.
    STEP 7: System receives activity/sleep/heart-rate data.
    STEP 8: Risk trajectory changes.
    STEP 9: AI detects deterioration.
    STEP 10: High-risk alert is generated.
    STEP 11: Clinician reviews the patient.
    STEP 12: Clinician creates/approves care plan.
    STEP 13: Citizen receives intervention.
    STEP 14: Follow-up measurement is recorded.
    STEP 15: Risk trajectory improves.
    STEP 16: Population dashboard shows aggregate impact.
    """
    return execute_all_challenge_steps()


@router.post("/challenge/step/{step_number}", response_model=ChallengeStepRecord)
@challenge_router.post("/step/{step_number}", response_model=ChallengeStepRecord)
async def run_challenge_step_endpoint(step_number: int):
    """Executes a single step (1 to 16) of the Seva Innovation Challenge Demo."""
    if not (1 <= step_number <= 16):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step number '{step_number}'. Must be between 1 and 16.",
        )
    return execute_challenge_step(step_number)


@router.get("/challenge/state", response_model=Dict[str, Any])
@challenge_router.get("/state", response_model=Dict[str, Any])
@challenge_router.get("/status", response_model=Dict[str, Any])
async def get_challenge_state_endpoint():
    """Retrieves live state and list of executed steps in the challenge demonstration."""
    return get_challenge_demo_state()


@router.get("/challenge/steps", response_model=List[Dict[str, Any]])
@challenge_router.get("/steps", response_model=List[Dict[str, Any]])
async def list_all_16_challenge_steps_metadata():
    """Lists the official schema and metadata of all 16 challenge demo steps."""
    step_catalog = [
        {"step_number": 1, "title": "Health worker registers citizen", "actor": "HEALTH_WORKER"},
        {"step_number": 2, "title": "Citizen completes NCD screening", "actor": "CITIZEN"},
        {"step_number": 3, "title": "System calculates risk", "actor": "SYSTEM"},
        {"step_number": 4, "title": "AI explains risk", "actor": "AI_ENGINE"},
        {"step_number": 5, "title": "System generates personalized prevention plan", "actor": "SYSTEM"},
        {"step_number": 6, "title": "Citizen connects wearable", "actor": "CITIZEN"},
        {"step_number": 7, "title": "System receives activity/sleep/heart-rate data", "actor": "SYSTEM"},
        {"step_number": 8, "title": "Risk trajectory changes", "actor": "SYSTEM"},
        {"step_number": 9, "title": "AI detects deterioration", "actor": "AI_ENGINE"},
        {"step_number": 10, "title": "High-risk alert is generated", "actor": "SYSTEM"},
        {"step_number": 11, "title": "Clinician reviews the patient", "actor": "CLINICIAN"},
        {"step_number": 12, "title": "Clinician creates/approves care plan", "actor": "CLINICIAN"},
        {"step_number": 13, "title": "Citizen receives intervention", "actor": "CITIZEN"},
        {"step_number": 14, "title": "Follow-up measurement is recorded", "actor": "HEALTH_WORKER"},
        {"step_number": 15, "title": "Risk trajectory improves", "actor": "SYSTEM"},
        {"step_number": 16, "title": "Population dashboard shows aggregate impact", "actor": "PUBLIC_HEALTH_ADMIN"},
    ]
    return step_catalog

