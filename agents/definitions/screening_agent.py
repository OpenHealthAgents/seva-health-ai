"""ScreeningAgent: Bounded agent for preventive health intake and screening questionnaires."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from agents.core.base import BoundedAgent
from agents.core.models import FailureBehavior, RetryPolicy


class ScreeningAgentInput(BaseModel):
    citizen_id: str
    age: int = Field(ge=1, le=120)
    gender: str = "MALE"
    waist_circumference_cm: float = Field(ge=40.0, le=200.0)
    physical_activity_level: str = "Sedentary"
    family_history_diabetes: str = "None"
    cbac_answers: Dict[str, Any] = Field(default_factory=dict)
    vitals: Dict[str, float] = Field(default_factory=dict)
    language: str = "en"


class ScreeningAgentOutput(BaseModel):
    citizen_id: str
    cbac_score: int
    cbac_high_risk: bool
    idrs_score: int
    idrs_risk_category: str
    composite_tier: str
    conversational_summary: str
    recommended_next_step: str
    deterministic_scoring_provenance: str
    language: str = "en"


class ScreeningAgent(BoundedAgent[ScreeningAgentInput, ScreeningAgentOutput]):
    """Bounded agent for citizen screening and questionnaire administration."""

    def __init__(self):
        super().__init__(
            name="ScreeningAgent",
            purpose=(
                "Guides citizens and community health workers through validated NCD screening checklists "
                "(CBAC and IDRS), validates physiological biometrics, and explains screening questions "
                "in culturally accessible local languages. NEVER diagnoses disease."
            ),
            allowed_tools=["calculate_cbac_score", "calculate_idrs_score"],
            input_schema=ScreeningAgentInput,
            output_schema=ScreeningAgentOutput,
            safety_constraints=[
                "NON_DIAGNOSTIC: Must clearly state that screening is not a clinical diagnosis.",
                "PHYSIOLOGICAL_VALIDATION: Rejects physiologically impossible biometrics.",
                "NO_PRESCRIBING: Cannot prescribe or recommend pharmaceutical drugs.",
            ],
            authorized_roles=[
                UserRole.CITIZEN,
                UserRole.HEALTH_WORKER,
                UserRole.CLINICIAN,
                UserRole.SYSTEM_ADMIN,
            ],
            timeout_sec=5.0,
            retry_policy=RetryPolicy(max_retries=2, initial_delay_ms=150),
            failure_behavior=FailureBehavior.FALLBACK_TO_DETERMINISTIC,
        )

    async def _process(self, input_data: ScreeningAgentInput, actor: TokenPayload) -> ScreeningAgentOutput:
        # 1. Deterministic Calculation for CBAC
        cbac_result = await self.invoke_tool(
            "calculate_cbac_score",
            responses=input_data.cbac_answers,
        )

        # 2. Deterministic Calculation for IDRS
        idrs_result = await self.invoke_tool(
            "calculate_idrs_score",
            age=input_data.age,
            waist_circumference_cm=input_data.waist_circumference_cm,
            physical_activity=input_data.physical_activity_level,
            family_history_diabetes=input_data.family_history_diabetes,
        )

        cbac_score = cbac_result["score"]
        is_cbac_high = cbac_result["is_high_risk"]
        idrs_score = idrs_result["score"]
        idrs_cat = idrs_result["risk_category"]

        # Composite tier determination
        if is_cbac_high or idrs_score >= 60:
            tier = "HIGH"
            next_step = "Refer citizen to Primary Health Centre (PHC) Medical Officer for confirmatory diagnostic testing."
            summary = (
                f"Screening complete. CBAC score is {cbac_score}/10 and Indian Diabetes Risk Score is {idrs_score}/100 "
                f"({idrs_cat} risk). Several lifestyle risk indicators are elevated, warranting medical evaluation."
            )
        elif idrs_score >= 30:
            tier = "MODERATE"
            next_step = "Enroll in community lifestyle modification program; schedule 6-month follow-up."
            summary = (
                f"Screening complete. IDRS score is {idrs_score}/100 ({idrs_cat} risk) and CBAC score is {cbac_score}/10. "
                "Moderate lifestyle risks identified. Preventative habits can significantly reduce future risk."
            )
        else:
            tier = "LOW"
            next_step = "Maintain healthy active lifestyle; schedule annual routine screening."
            summary = (
                f"Screening complete. Both CBAC ({cbac_score}/10) and IDRS ({idrs_score}/100) indicate low current risk. "
                "Keep up balanced nutrition and regular physical activity."
            )

        return ScreeningAgentOutput(
            citizen_id=input_data.citizen_id,
            cbac_score=cbac_score,
            cbac_high_risk=is_cbac_high,
            idrs_score=idrs_score,
            idrs_risk_category=idrs_cat,
            composite_tier=tier,
            conversational_summary=summary,
            recommended_next_step=next_step,
            deterministic_scoring_provenance="MOHFW CBAC + MDRF IDRS Engines",
            language=input_data.language,
        )

    async def _fallback(self, input_data: ScreeningAgentInput, actor: TokenPayload, error: Exception) -> ScreeningAgentOutput:
        # Pure deterministic rule execution without conversational synthesis
        from packages.clinical_models.screening import CBACSurvey, IDRSSurvey
        from services.screening.calculator import calculate_cbac, calculate_idrs

        cbac_survey = CBACSurvey(
            age_over_30=input_data.cbac_answers.get("age_over_30", False),
            tobacco_user=input_data.cbac_answers.get("tobacco_user", False),
            alcohol_consumption=input_data.cbac_answers.get("alcohol_consumption", False),
            waist_circumference_exceeded=input_data.cbac_answers.get("waist_circumference_exceeded", False),
            physical_activity_below_150min=input_data.cbac_answers.get("physical_activity_below_150min", False),
            family_history_diabetes_or_htn=input_data.cbac_answers.get("family_history_diabetes_or_htn", False),
        )
        cbac = calculate_cbac(cbac_survey)

        age_cat = ">=50" if input_data.age >= 50 else ("35-49" if input_data.age >= 35 else "<35")
        waist_cat = ">=100" if input_data.waist_circumference_cm >= 100 else ("90-99" if input_data.waist_circumference_cm >= 90 else "<90")
        idrs_survey = IDRSSurvey(
            age_category=age_cat,
            waist_category=waist_cat,
            physical_activity=input_data.physical_activity_level if input_data.physical_activity_level in ["None", "Sedentary", "Moderate", "Vigorous"] else "Sedentary",
            family_history=input_data.family_history_diabetes if input_data.family_history_diabetes in ["None", "One parent", "Both parents"] else "None",
        )
        idrs = calculate_idrs(idrs_survey)
        tier = "HIGH" if (cbac >= 4 or idrs >= 60) else ("MODERATE" if idrs >= 30 else "LOW")

        return ScreeningAgentOutput(
            citizen_id=input_data.citizen_id,
            cbac_score=cbac,
            cbac_high_risk=cbac >= 4,
            idrs_score=idrs,
            idrs_risk_category="HIGH" if idrs >= 60 else ("MODERATE" if idrs >= 30 else "LOW"),
            composite_tier=tier,
            conversational_summary=f"Automated calculation: CBAC score {cbac}, IDRS score {idrs}.",
            recommended_next_step="Consult healthcare worker for detailed assessment.",
            deterministic_scoring_provenance="Deterministic Fallback Scorer",
            language=input_data.language,
        )
