from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import uuid

from packages.clinical_models.screening import (
    ScreeningSession,
    ScreeningSessionCreate,
)
from packages.clinical_models.observations import Observation
from packages.clinical_models.terminology import LOINC_CODES
from packages.auth.jwt import get_current_user_token, TokenPayload
from packages.types.enums import AuditAction
from packages.observability.audit import audit_logger
from services.screening.calculator import calculate_idrs, calculate_cbac
from services.screening.questionnaire_models import (
    QuestionnaireWorkflowProfile,
    ConfigurableScreeningSubmission,
    ScreeningEvaluationResponse,
    ExplainableScreeningSummary,
)
from services.screening.questionnaire_engine import QuestionnaireEngine, WORKFLOW_PROFILES
from services.store import store

router = APIRouter(prefix="/screening", tags=["Preventive Screening Engine"])


@router.get("/questionnaire/config", response_model=QuestionnaireWorkflowProfile)
async def get_questionnaire_config(
    workflow: str = "mvp_comprehensive"
):
    """Returns the dynamic, configurable questionnaire protocol definition.
    Allows frontend clients to render form controls without hardcoding fields into UI code.
    """
    return QuestionnaireEngine.get_profile(workflow)


@router.post("/evaluate-configurable", response_model=ScreeningEvaluationResponse)
async def evaluate_configurable_screening(
    submission: ConfigurableScreeningSubmission,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Processes dynamic questionnaire answers, generates structured LOINC observations,
    triggers NCD risk evaluation, and generates an explainable summary.
    """
    try:
        result = QuestionnaireEngine.evaluate_submission(
            submission=submission,
            actor_id=current_user.sub,
            actor_role=current_user.role,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Screening evaluation failed: {str(e)}")


@router.get("/evaluate-demo/{scenario}", response_model=ScreeningEvaluationResponse)
async def evaluate_demo_screening(
    scenario: str = "rajesh_kumar_asha",
    current_user: TokenPayload = Depends(get_current_user_token)
):
    """Executes a 5-10 minute demonstration screening scenario with realistic synthetic personas:
    - rajesh_kumar_asha: 51M, ASHA field camp, prediabetic with central adiposity
    - sunita_sharma_citizen: 44F, citizen self-check, elevated vascular strain
    - vikram_singh_clinic: 54M, comprehensive PHC clinic intake with lipid profile
    """
    # Pick or ensure demo citizen exists
    target_citizen_id = "citizen-ramesh-patel-01"
    citizen = store.get_citizen(target_citizen_id)
    if not citizen:
        # Fallback to first citizen in store
        all_cit = store.list_citizens("tenant-karnataka-moh")
        if all_cit:
            target_citizen_id = all_cit[0].id

    demo_answers: Dict[str, Any] = {}
    if scenario == "rajesh_kumar_asha":
        demo_answers = {
            "age": 51,
            "sex": "MALE",
            "height": 168.0,
            "weight": 78.5,
            "waist_circumference": 98.0,
            "systolic_bp": 142.0,
            "diastolic_bp": 90.0,
            "heart_rate": 78.0,
            "fasting_glucose": 118.0,
            "hba1c": 6.2,
            "physical_activity": "Sedentary",
            "diet_quality": "High refined carbs / sweets / fried foods",
            "sleep_hours": 5.5,
            "smoking": "CURRENT_SMOKER",
            "alcohol": "NONE",
            "stress_level": 7.0,
            "family_history": ["DIABETES_ONE_PARENT", "HYPERTENSION"],
            "known_conditions": ["NONE"],
            "medication_history": ["NONE"],
        }
    elif scenario == "sunita_sharma_citizen":
        demo_answers = {
            "age": 44,
            "sex": "FEMALE",
            "height": 158.0,
            "weight": 68.0,
            "waist_circumference": 86.0,
            "systolic_bp": 136.0,
            "diastolic_bp": 88.0,
            "heart_rate": 72.0,
            "fasting_glucose": 104.0,
            "hba1c": 5.8,
            "physical_activity": "Moderate",
            "diet_quality": "Moderate mixed diet",
            "sleep_hours": 6.5,
            "smoking": "NEVER",
            "alcohol": "NONE",
            "stress_level": 8.0,
            "family_history": ["HYPERTENSION"],
            "known_conditions": ["NONE"],
            "medication_history": ["NONE"],
        }
    else:  # vikram_singh_clinic
        demo_answers = {
            "age": 54,
            "sex": "MALE",
            "height": 172.0,
            "weight": 84.0,
            "waist_circumference": 102.0,
            "systolic_bp": 148.0,
            "diastolic_bp": 94.0,
            "heart_rate": 82.0,
            "fasting_glucose": 124.0,
            "hba1c": 6.4,
            "total_cholesterol": 240.0,
            "ldl_cholesterol": 152.0,
            "hdl_cholesterol": 38.0,
            "triglycerides": 210.0,
            "serum_creatinine": 1.15,
            "physical_activity": "None",
            "diet_quality": "High refined carbs / sweets / fried foods",
            "sleep_hours": 5.0,
            "smoking": "CURRENT_SMOKER",
            "alcohol": "REGULAR",
            "stress_level": 8.0,
            "family_history": ["DIABETES_BOTH_PARENTS", "PREMATURE_CAD"],
            "known_conditions": ["DYSLIPIDEMIA"],
            "medication_history": ["AYURVEDIC_HERBAL"],
        }

    submission = ConfigurableScreeningSubmission(
        citizen_id=target_citizen_id,
        workflow_id="mvp_comprehensive",
        answers=demo_answers,
        notes=f"5-Minute Guided Demo Screening Scenario: {scenario}",
        screening_location="DEMO_FIELD_PORTAL",
    )

    return QuestionnaireEngine.evaluate_submission(
        submission=submission,
        actor_id=current_user.sub,
        actor_role=current_user.role,
    )


@router.post("/", response_model=ScreeningSession)
async def submit_screening(
    payload: ScreeningSessionCreate,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    citizen = store.get_citizen(payload.citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")

    idrs_score = calculate_idrs(payload.idrs) if payload.idrs else None
    cbac_score = calculate_cbac(payload.cbac) if payload.cbac else None

    session = ScreeningSession(
        id=str(uuid.uuid4()),
        tenant_id=citizen.tenant_id,
        citizen_id=payload.citizen_id,
        conducted_by_id=current_user.sub,
        conducted_at=datetime.now(timezone.utc),
        cbac=payload.cbac,
        idrs=payload.idrs,
        vitals=payload.vitals,
        notes=payload.notes,
        calculated_idrs_score=idrs_score,
        calculated_cbac_score=cbac_score,
    )
    store.add_screening(session)

    # Ingest discrete observations into LOINC store
    if payload.vitals:
        v = payload.vitals
        vital_mapping = [
            ("SYSTOLIC_BP", v.systolic_bp),
            ("DIASTOLIC_BP", v.diastolic_bp),
            ("HEART_RATE", v.heart_rate),
            ("FASTING_GLUCOSE", v.fasting_glucose),
            ("HBA1C", v.hba1c),
            ("TOTAL_CHOLESTEROL", v.total_cholesterol),
            ("HDL_CHOLESTEROL", v.hdl_cholesterol),
            ("TRIGLYCERIDES", v.triglycerides),
            ("BMI", v.bmi),
            ("WAIST_CIRCUMFERENCE", v.waist_circumference),
            ("EGFR", v.egfr),
        ]
        for key, val in vital_mapping:
            if val is not None and key in LOINC_CODES:
                meta = LOINC_CODES[key]
                obs = Observation(
                    id=str(uuid.uuid4()),
                    tenant_id=citizen.tenant_id,
                    citizen_id=citizen.id,
                    code=key,
                    value=float(val),
                    unit=meta.get("unit", ""),
                    loinc_code=meta["code"],
                    display_name=meta["display"],
                    source="SCREENING_SESSION",
                )
                store.add_observation(obs)

    audit_logger.record(
        tenant_id=citizen.tenant_id,
        actor_id=current_user.sub,
        actor_role=current_user.role,
        action=AuditAction.SCREENING_SUBMITTED,
        resource_type="ScreeningSession",
        resource_id=session.id,
    )

    return session


@router.get("/history/{citizen_id}", response_model=List[ScreeningSession])
async def get_screening_history(
    citizen_id: str,
    current_user: TokenPayload = Depends(get_current_user_token)
):
    return store.get_citizen_screenings(citizen_id)

