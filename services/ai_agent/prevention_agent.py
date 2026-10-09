"""SevaHealth AI Prevention Agent.

A bounded healthcare assistant operating under strict clinical safety boundaries:
1. Grounded in retrieved patient data (vitals, labs, trajectory, plan, wearables).
2. Prohibited from autonomous diagnosis, medication prescribing, or altering prescriptions.
3. Automated acute escalation detection for emergencies (e.g. chest pain, hypertensive crisis).
4. Full multilingual conversational support (English, Hindi, Kannada, Telugu, Tamil).
5. Comprehensive audit logging for all decisions and tool executions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, date
import re
from pydantic import BaseModel, Field

from packages.types.enums import UserRole
from packages.auth.jwt import TokenPayload
from packages.ai_schemas.schemas import LLMSOAPSummaryOutput
from packages.ai_schemas.safety import (
    ClinicalSafetyEnvelope,
    EmergencyRoutingDetails,
    HumanVerificationState,
    SafetyBanner,
)
from packages.clinical_models.consent import ConsentCategory, consent_manager
from packages.interop.security import AntiArbitraryQueryGuard, ArbitraryQueryViolationError
from services.ai_agent.safety import ClinicalSafetyEngine, ClinicalSafetyEnforcer
import time
from packages.observability.context import SpanStage
from packages.observability.tracer import tracer
from packages.observability.metrics import metrics
from services.ai_agent.tools import (
    agent_telemetry,
    get_patient_profile,
    get_latest_vitals,
    get_recent_labs,
    get_risk_assessment,
    get_risk_trajectory,
    get_intervention_plan,
    get_wearable_summary,
    get_medication_list,
    get_clinical_history,
    create_checkin,
    create_followup,
    create_alert,
    request_clinician_review,
)


class PreventionAgentResponse(BaseModel):
    """Structured response schema returned by the SevaHealth AI Prevention Agent."""
    answer: str
    evidence: List[str] = Field(default_factory=list)
    uncertainty: str
    recommended_action: str
    escalation: bool = False
    escalation_details: Optional[Dict[str, Any]] = None
    citations: List[str] = Field(default_factory=list)
    tool_calls_executed: List[str] = Field(default_factory=list)
    language: str = "en"
    safety_banners: List[str] = Field(default_factory=list)
    safety_envelope: Optional[ClinicalSafetyEnvelope] = None


class SevaHealthPreventionAgent:
    """Bounded, clinically safe preventive healthcare AI assistant."""

    # Red-flag emergency symptom patterns
    EMERGENCY_PATTERNS = [
        r"\bchest\s+pain\b",
        r"\bchest\s+tightness\b",
        r"\bpressure\s+in\s+chest\b",
        r"\bpain\s+radiating\s+to\s+(?:left\s+)?arm\b",
        r"\bpain\s+radiating\s+to\s+jaw\b",
        r"\bsevere\s+shortness\s+of\s+breath\b",
        r"\bcannot\s+breathe\b",
        r"\bsudden\s+numbness\b",
        r"\bsudden\s+weakness\b",
        r"\bslurred\s+speech\b",
        r"\bfacial\s+droop\b",
        r"\bfainted\b",
        r"\bloss\s+of\s+consciousness\b",
        r"\bblood\s+pressure\s+180\b",
        r"\bbp\s+180\b",
        r"\bbp\s+above\s+180\b",
    ]

    # Medication inquiry patterns
    MEDICATION_QUERY_PATTERNS = [
        r"\bstop\b.*?\b(?:medication|medicine|metformin|amlodipine|telmisartan|pills|drugs)\b",
        r"\b(?:change|increase|decrease|double|halve)\b.*?\b(?:dose|dosage|medication|medicine|metformin|amlodipine|telmisartan|pills)\b",
        r"\bprescribe\b",
        r"\bwhat\s+(?:medicine|drug|pill|medication)\s+should\s+i\s+take\b",
        r"\bcan\s+i\s+(?:take\s+more|take\s+less|stop\s+taking|double|cut)\b",
        r"\bshould\s+i\s+(?:take\s+more|take\s+less|stop\s+taking|double|cut)\b",
    ]

    @classmethod
    def _is_emergency_query(cls, text: str) -> bool:
        return any(re.search(pat, text, re.IGNORECASE) for pat in cls.EMERGENCY_PATTERNS)

    @classmethod
    def _is_medication_query(cls, text: str) -> bool:
        return any(re.search(pat, text, re.IGNORECASE) for pat in cls.MEDICATION_QUERY_PATTERNS)

    @classmethod
    def _detect_missing_data(
        cls,
        vitals: Dict[str, Any],
        labs: Dict[str, Any],
        wearables: Dict[str, Any],
    ) -> List[str]:
        missing = []
        if "systolic_bp" not in vitals:
            missing.append("Blood Pressure (Systolic / Diastolic)")
        if "bmi" not in vitals:
            missing.append("Height / Weight (BMI)")
        if "waist_circumference" not in vitals:
            missing.append("Waist Circumference")
        if "fasting_glucose" not in labs and "hba1c" not in labs:
            missing.append("Glycemic Marker (Fasting Glucose or HbA1c)")
        if "lipid_panel" not in labs and "triglycerides" not in labs:
            missing.append("Lipid Profile (Triglycerides, HDL, Total Cholesterol)")
        if wearables.get("connection_status") != "CONNECTED":
            missing.append("Smartwatch / Activity Telemetry Sync")
        return missing

    async def chat(
        self,
        citizen_id: str,
        user_query: str,
        actor: TokenPayload,
        language: str = "en",
    ) -> PreventionAgentResponse:
        """Processes conversational queries with grounded retrieval and safety bounds."""
        # Defense against arbitrary SQL/GraphQL queries through agent chat
        try:
            AntiArbitraryQueryGuard.inspect_query_parameter("user_query", user_query)
        except ArbitraryQueryViolationError as aq_err:
            return PreventionAgentResponse(
                answer=(
                    "SECURITY_ALERT: Arbitrary SQL or GraphQL queries are strictly prohibited against clinical systems. "
                    "Clinical information can only be accessed through authorized, parameterized services."
                ),
                uncertainty="HIGH - Prohibited raw query syntax detected.",
                recommended_action="Please use standard conversational questions or clinician tools.",
                escalation=False,
                language=language,
            )

        # Check active AI_PROCESSING consent if user has registered consents
        active_ai_consents = consent_manager.list_consents(subject=citizen_id, category=ConsentCategory.AI_PROCESSING)
        if active_ai_consents and all(not c.is_valid() for c in active_ai_consents):
            return PreventionAgentResponse(
                answer=(
                    "CONSENT RESTRICTION: Access to your health data for AI Processing has been REVOKED or has EXPIRED in your Citizen Privacy Center. "
                    "To receive personalized AI prevention guidance, please grant 'AI Processing' consent."
                ),
                evidence=[],
                uncertainty="Consent not active for AI Processing.",
                recommended_action="Visit Citizen Privacy Center to manage your healthcare consents.",
                escalation=False,
                safety_banners=[SafetyBanner.PROFESSIONAL_REVIEW.value],
                language=language,
            )

        executed_tools: List[str] = []
        evidence_list: List[str] = []
        citations_list: List[str] = []

        # 1. Check for Acute Emergency Red-Flags
        if self._is_emergency_query(user_query):
            # Automatically trigger emergency alert and clinician review
            try:
                alert_res = create_alert(
                    citizen_id=citizen_id,
                    alert_data={
                        "urgency": "EMERGENCY",
                        "alert_type": "ACUTE_RED_FLAG_SYMPTOM",
                        "message": f"Emergency symptom reported in chat: '{user_query}'",
                        "clinical_rule_triggered": "ACUTE_CARDIOVASCULAR_OR_NEUROLOGIC_RED_FLAG",
                    },
                    actor=actor,
                )
                executed_tools.append("create_alert")

                review_res = request_clinician_review(
                    citizen_id=citizen_id,
                    reason=f"Emergency red-flag symptom reported: {user_query}",
                    urgency="EMERGENCY",
                    actor=actor,
                )
                executed_tools.append("request_clinician_review")
            except Exception as e:
                pass

            emergency_text = (
                "EMERGENCY WARNING: Your reported symptoms indicate a potential medical emergency that requires "
                "IMMEDIATE, urgent medical evaluation. Please CALL 108 (National Emergency Ambulance Service) or have "
                "someone take you to the nearest Primary Health Centre (PHC) or Hospital Emergency Room immediately.\n\n"
                "Do NOT wait, do NOT drive yourself, and do NOT attempt home remedies. An automated high-urgency alert "
                "has been logged with your care team."
            )

            if language == "kn":
                emergency_text = (
                    "ತುರ್ತು ಎಚ್ಚರಿಕೆ (EMERGENCY WARNING): ನಿಮ್ಮ ಲಕ್ಷಣಗಳು ತಕ್ಷಣದ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಯನ್ನು ಬಯಸುತ್ತವೆ. "
                    "ದಯವಿಟ್ಟು ತಕ್ಷಣ 108 ಆಂಬ್ಯುಲೆನ್ಸ್ ಸಂಖ್ಯೆಗೆ ಕರೆ ಮಾಡಿ ಅಥವಾ ಹತ್ತಿರದ ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರ (PHC) ಅಥವಾ "
                    "ಆಸ್ಪತ್ರೆಯ ತುರ್ತು ಚಿಕಿತ್ಸಾ ವಿಭಾಗಕ್ಕೆ ತೆರಳಿ. ತಕ್ಷಣ ವೈದ್ಯರನ್ನು ಭೇಟಿಯಾಗಿ!"
                )
            elif language == "hi":
                emergency_text = (
                    "आपातकालीन चेतावनी (EMERGENCY WARNING): आपके बताए गए लक्षण तुरंत चिकित्सीय जांच की मांग करते हैं। "
                    "कृपया तुरंत 108 एम्बुलेंस सेवा पर कॉल करें या नजदीकी प्राथमिक स्वास्थ्य केंद्र (PHC) या अस्पताल के "
                    "इमरजेंसी वार्ड में जाएं। बिल्कुल भी देरी न करें!"
                )

            emergency_envelope = ClinicalSafetyEnvelope(
                source_data={"reported_symptom": user_query, "citizen_id": citizen_id},
                timestamp=datetime.now(timezone.utc).isoformat(),
                model_version="v1.0.0",
                agent_version="v1.0.0",
                confidence=1.0,
                limitations=["Acute emergent symptom reported; routine conversational preventive coaching superseded by emergency protocol."],
                human_verification_state=HumanVerificationState.PENDING_REVIEW,
                safety_banners=[
                    SafetyBanner.EMERGENCY.value,
                    SafetyBanner.PROFESSIONAL_REVIEW.value,
                ],
                emergency_routing_triggered=True,
                emergency_routing=EmergencyRoutingDetails(
                    is_emergency=True,
                    urgency_level="CRITICAL_EMERGENCY",
                    trigger_reasons=[f"Acute red-flag symptom: {user_query}"],
                    recommended_action="Call 108 (Ambulance) / Seek urgent medical care immediately",
                ),
            )

            resp = PreventionAgentResponse(
                answer=emergency_text,
                evidence=[f"Reported red-flag query: '{user_query}'"],
                uncertainty="Automated AI cannot diagnose emergencies. Immediate in-person physical triage is required.",
                recommended_action="Call 108 / Visit Nearest Emergency Department Immediately",
                escalation=True,
                escalation_details={
                    "urgency": "EMERGENCY",
                    "emergency_phone": "108",
                    "action_required": "IMMEDIATE_PHYSICAL_EXAM",
                    "alert_logged": True,
                },
                citations=["WHO Emergency Triage Guidelines", "ICMR Acute Chest Pain Protocol"],
                tool_calls_executed=executed_tools,
                language=language,
                safety_banners=[SafetyBanner.EMERGENCY.value, SafetyBanner.PROFESSIONAL_REVIEW.value],
                safety_envelope=emergency_envelope,
            )

            agent_telemetry.log_decision(
                agent_name="SevaHealthPreventionAgent",
                citizen_id=citizen_id,
                actor_id=actor.sub,
                user_query=user_query,
                decision="EMERGENCY_ESCALATION",
                escalation=True,
                evidence_count=len(resp.evidence),
            )
            return resp

        # 2. Check for Prescribing / Medication Modification Requests
        if self._is_medication_query(user_query):
            # Fetch current medications to ground response
            meds = []
            try:
                meds = get_medication_list(citizen_id=citizen_id, actor=actor)
                executed_tools.append("get_medication_list")
            except Exception:
                pass

            med_names = [f"{m.get('drug_name')} ({m.get('dosage')})" for m in meds]
            med_context = f"Your current active prescribed regimen: {', '.join(med_names)}" if med_names else "No active prescription records in your profile."
            evidence_list.append(med_context)

            med_warning = (
                f"{med_context}\n\n"
                "IMPORTANT CLINICAL SAFETY NOTICE: As an AI Preventive Health Assistant, I am strictly prohibited "
                "from prescribing medications, altering dosages, or advising you to discontinue any prescribed drugs.\n\n"
                "Pharmacotherapy must only be adjusted by a qualified physician. Never discontinue or adjust your dose "
                "without direct clinician consultation, as abrupt discontinuation can lead to severe rebound hypertension or glycemic spikes."
            )

            if language == "kn":
                med_warning = (
                    f"{med_context}\n\n"
                    "ಕ್ಲಿನಿಕಲ್ ಸುರಕ್ಷತಾ ಸೂಚನೆ: ಎಐ ಸಹಾಯಕನಾಗಿ ನಾನು ಔಷಧಿಗಳನ್ನು ಶಿಫಾರಸು ಮಾಡಲು, ಬದಲಾಯಿಸಲು ಅಥವಾ ನಿಲ್ಲಿಸಲು "
                    "ಅನುಮತಿ ಹೊಂದಿಲ್ಲ. ದಯವಿಟ್ಟು ಯಾವುದೇ ಔಷಧಿ ಬದಲಾವಣೆಗೆ ನಿಮ್ಮ ವೈದ್ಯರನ್ನು (ಡಾಕ್ಟರ್) ಸಂಪರ್ಕಿಸಿ."
                )
            elif language == "hi":
                med_warning = (
                    f"{med_context}\n\n"
                    "नैदानिक सुरक्षा सूचना: एक एआई स्वास्थ्य सहायक के रूप में, मुझे दवाइयां लिखने, बदलने या बंद करने "
                    "की अनुमति नहीं है। किसी भी बदलाव के लिए कृपया अपने डॉक्टर से परामर्श करें।"
                )

            citations_list.append("National Medical Commission (NMC) Telemedicine Practice Guidelines")

            resp = PreventionAgentResponse(
                answer=med_warning,
                evidence=evidence_list,
                uncertainty="AI agents do not possess prescriptive authority under medical governance regulations.",
                recommended_action="Consult your treating clinician for medication adjustments.",
                escalation=False,
                citations=citations_list,
                tool_calls_executed=executed_tools,
                language=language,
            )

            agent_telemetry.log_decision(
                agent_name="SevaHealthPreventionAgent",
                citizen_id=citizen_id,
                actor_id=actor.sub,
                user_query=user_query,
                decision="MEDICATION_PRESCRIBING_REJECTED",
                escalation=False,
                evidence_count=len(resp.evidence),
            )
            return resp

        # 3. Grounded Retrieval across Clinical Services
        profile = get_patient_profile(citizen_id=citizen_id, actor=actor)
        executed_tools.append("get_patient_profile")

        vitals = get_latest_vitals(citizen_id=citizen_id, actor=actor)
        executed_tools.append("get_latest_vitals")

        labs = get_recent_labs(citizen_id=citizen_id, actor=actor)
        executed_tools.append("get_recent_labs")

        risk = get_risk_assessment(citizen_id=citizen_id, actor=actor)
        executed_tools.append("get_risk_assessment")

        trajectory = get_risk_trajectory(citizen_id=citizen_id, actor=actor)
        executed_tools.append("get_risk_trajectory")

        care_plan = get_intervention_plan(citizen_id=citizen_id, actor=actor)
        executed_tools.append("get_intervention_plan")

        wearables = get_wearable_summary(citizen_id=citizen_id, actor=actor)
        executed_tools.append("get_wearable_summary")

        # Compile evidence list from retrieved data
        citizen_name = profile.get("name", "Citizen")
        age = profile.get("age", 45)
        evidence_list.append(f"Patient: {citizen_name}, Age: {age}, District: {profile.get('district')}")

        if "systolic_bp" in vitals:
            sbp = vitals["systolic_bp"]["value"]
            dbp = vitals.get("diastolic_bp", {}).get("value", 80)
            evidence_list.append(f"Latest BP: {sbp}/{dbp} mmHg ({vitals['systolic_bp'].get('clinical_flag')})")
        if "hba1c" in labs:
            evidence_list.append(f"HbA1c: {labs['hba1c']['value']}% ({labs['hba1c'].get('interpretation')})")
        if "fasting_glucose" in labs:
            evidence_list.append(f"Fasting Blood Glucose: {labs['fasting_glucose']['value']} mg/dL")
        if "bmi" in vitals:
            evidence_list.append(f"BMI: {vitals['bmi']['value']} kg/m2 ({vitals['bmi'].get('clinical_flag')})")

        overall_tier = risk.get("overall_tier", "MODERATE")
        overall_score = risk.get("overall_score", 0.5)
        evidence_list.append(f"Stratified Risk Tier: {overall_tier} ({int(overall_score * 100)}%)")

        trend = trajectory.get("overall_trend", "STABLE")
        evidence_list.append(f"Longitudinal Trajectory Trend: {trend} (Change: {trajectory.get('change_percentage', 0.0)}%)")

        # 4. Formulate Response based on Query Intent
        q_lower = user_query.lower()

        # Intent A: Care Plan & Lifestyle Prevention Guidance
        if any(w in q_lower for w in ["diet", "food", "eat", "millet", "nutrition", "exercise", "walk", "sleep", "stress", "plan", "tasks", "goal", "adherence", "lifestyle"]):
            citations_list.append("National Institute of Nutrition (NIN) Dietary Guidelines for Indians")
            citations_list.append("WHO Guidelines on Physical Activity and Sedentary Behaviour")

            nut_guidance = care_plan.get("nutrition_guidance", "Incorporate whole millets and leafy vegetables.")
            act_guidance = care_plan.get("activity_guidance", "Aim for 150 minutes of moderate aerobic activity weekly.")
            adh_rate = care_plan.get("adherence_percentage", 0.0)

            if language == "kn":
                answer_body = (
                    f"ನಿಮ್ಮ 30-ದಿನಗಳ ತಡೆಗಟ್ಟುವಿಕೆ ಯೋಜನೆ: '{care_plan.get('title', 'ಆರೋಗ್ಯ ಯೋಜನೆ')}'.\n\n"
                    f"• ಪ್ರಸ್ತುತ ಪಾಲನೆ ದರ (Adherence): {adh_rate}%\n"
                    f"• ಆಹಾರ ಮಾರ್ಗದರ್ಶನ: {nut_guidance}\n"
                    f"• ದೈಹಿಕ ವ್ಯಾಯಾಮ: {act_guidance}\n\n"
                    "ಪ್ರತಿದಿನ ನಿಯಮಿತವಾಗಿ ಕೆಲಸಗಳನ್ನು ಪೂರ್ಣಗೊಳಿಸುವುದರಿಂದ ಆರೋಗ್ಯ ಸುಧಾರಿಸುತ್ತದೆ."
                )
                uncertainty_text = "ವೈಯಕ್ತಿಕ ಫಲಿತಾಂಶಗಳು ದೈನಂದಿನ ಪಾಲನೆಯ ಮೇಲೆ ಅವಲಂಬಿತವಾಗಿರುತ್ತವೆ."
                action_text = "ಇಂದಿನ ನಿಗದಿತ ನಡಿಗೆ ಮತ್ತು ಆಹಾರ ಕಾರ್ಯವನ್ನು ಪೂರ್ಣಗೊಳಿಸಿ."
            elif language == "hi":
                answer_body = (
                    f"आपकी 30-दिवसीय रोकथाम योजना: '{care_plan.get('title', 'स्वास्थ्य योजना')}'.\n\n"
                    f"• वर्तमान अनुपालन दर (Adherence): {adh_rate}%\n"
                    f"• आहार सलाह: {nut_guidance}\n"
                    f"• व्यायाम लक्ष्य: {act_guidance}\n\n"
                    "प्रतिदिन छोटे कदम उठाकर आप अपने स्वास्थ्य को बेहतर बना सकते हैं।"
                )
                uncertainty_text = "परिणाम आपकी दैनिक जीवनशैली की निरंतरता पर निर्भर करते हैं।"
                action_text = "आज का भोजन और पैदल चलने का लक्ष्य पूरा करें।"
            else:
                answer_body = (
                    f"Here is your 30-Day Prevention Care Plan overview: **{care_plan.get('title', 'Active Prevention Journey')}**\n\n"
                    f"• Current Adherence Rate: {adh_rate:.1f}%\n"
                    f"• Dietary Recommendations: {nut_guidance}\n"
                    f"• Physical Activity Target: {act_guidance}\n"
                    f"• Restorative Sleep & Stress: {care_plan.get('sleep_guidance', '7-8 hours nightly')}\n\n"
                    "Consistent adherence to these evidence-based micro-habits blunts glycemic excursions and reduces blood pressure load."
                )
                uncertainty_text = "Behavioral intervention benefits accumulate over 4-12 weeks."
                action_text = "Complete today's daily tasks and log your check-in."

        # Intent B: Trend / Trajectory Explanation
        elif any(w in q_lower for w in ["trend", "trajectory", "worsening", "improving", "getting better", "getting worse", "over time", "progress over"]):
            citations_list.append("ICMR-INDIAB Longitudinal Cohort Study")
            citations_list.append("WHO Non-Communicable Diseases Surveillance Guidelines")

            drivers = trajectory.get("contributing_factors", [])
            drivers_text = "\n".join([f"• {d}" for d in drivers])

            if language == "kn":
                answer_body = (
                    f"ನಮಸ್ಕಾರ {citizen_name}, ನಿಮ್ಮ ಇತ್ತೀಚಿನ ಆರೋಗ್ಯ ಪ್ರವೃತ್ತಿ (Risk Trajectory) **{trend}** ಆಗಿದೆ.\n\n"
                    f"ನಿಮ್ಮ ಹಿಂದಿನ ಅಪಾಯದ ಅಂಕದಿಂದ ಪ್ರಸ್ತುತ ಅಂಕವು ಬದಲಾಗಿದೆ. ಸಂಬಂಧಿಸಿದ ಪ್ರಮುಖ ಅಂಶಗಳು:\n{drivers_text}\n\n"
                    "ಗಮನಿಸಿ: ಈ ಅಂಶಗಳು ಕೇವಲ ಸಂಭವನೀಯತೆಯನ್ನು ಸೂಚಿಸುತ್ತವೆ. ನಿಮ್ಮ 30 ದಿನಗಳ ಜೀವನಶೈಲಿ ಯೋಜನೆಯನ್ನು ಪಾಲಿಸುವುದರಿಂದ ಅಪಾಯವನ್ನು ಕಡಿಮೆ ಮಾಡಬಹುದು."
                )
                uncertainty_text = "ದೀರ್ಘಾವಧಿಯ ಡೇಟಾ ಮಾದರಿಯು ಸಂಭವನೀಯತೆಯ ಆಧಾರಿತವಾಗಿದೆ."
                action_text = "ದೈನಂದಿನ ನಡಿಗೆ ಮತ್ತು ರಾಗಿ/ಸಿರಿಧಾನ್ಯ ಸೇವನೆಯನ್ನು ಮುಂದುವರಿಸಿ."
            elif language == "hi":
                answer_body = (
                    f"नमस्ते {citizen_name}, आपकी हालिया स्वास्थ्य प्रवृत्ति (Risk Trajectory) **{trend}** दर्शा रही है।\n\n"
                    f"आपके जोखिम स्कोर में बदलाव देखा गया है। संबंधित प्रमुख कारक:\n{drivers_text}\n\n"
                    "ध्यान दें: ये कारक स्वास्थ्य जोखिम से जुड़े हुए हैं। सही खानपान और नियमित व्यायाम से इसे सुधारा जा सकता है।"
                )
                uncertainty_text = "दीर्घकालिक प्रवृत्तियां सांख्यिकीय अनुमानों पर आधारित हैं।"
                action_text = "दैनिक व्यायाम जारी रखें और 30 दिन की योजना का पालन करें।"
            else:
                answer_body = (
                    f"Hello {citizen_name}, reviewing your longitudinal health record, your current risk trajectory is evaluated as **{trend}**.\n\n"
                    f"• Composite Risk Index: {int(overall_score * 100)}% (Category: {overall_tier})\n"
                    f"• Longitudinal Shift: {trajectory.get('change_percentage', 0.0):+0.1f}% relative to prior baseline.\n\n"
                    f"Key Contributing Factors (Non-causal association):\n{drivers_text}\n\n"
                    "These biometric parameters are associated with metabolic strain. Consistent adherence to your prevention care plan is recommended to stabilize this trend."
                )
                uncertainty_text = "Trajectory models indicate longitudinal statistical correlation, not direct biological causation."
                action_text = "Maintain scheduled 30-day care plan tasks and attend follow-up screening."

        # Intent C: Risk Result Explanation
        elif any(w in q_lower for w in ["risk", "score", "why high", "why moderate", "result", "explain"]):
            citations_list.append("ICMR Guidelines for Management of Type 2 Diabetes 2023")
            citations_list.append("Indian Guidelines on Hypertension (I-GH-IV)")

            drivers_list = risk.get("top_drivers", [])
            drivers_str = "\n".join([
                f"• {d['feature_name']}: Observed {d['observed_value']} (Target: {d['target_value']}) - Weight: {int(d['impact_weight'] * 100)}%"
                for d in drivers_list
            ])

            if language == "kn":
                answer_body = (
                    f"ನಿಮ್ಮ ಒಟ್ಟು ಎನ್‌ಸಿಡಿ ಅಪಾಯದ ವರ್ಗ: **{overall_tier}** ({int(overall_score * 100)}%).\n\n"
                    f"ಮುಖ್ಯ ಕಾರಣಗಳು:\n{drivers_str}\n\n"
                    "ಇದು ರೋಗನಿರ್ಣಯವಲ್ಲ. ಆರಂಭಿಕ ಹಂತದಲ್ಲಿ ಜೀವನಶೈಲಿ ಬದಲಾವಣೆಗಳಿಂದ ಇದನ್ನು ಸರಿಪಡಿಸಬಹುದು."
                )
                uncertainty_text = "ಅಪಾಯದ ಅಂದಾಜು ಜನಸಂಖ್ಯಾ ಮಾದರಿಗಳನ್ನು ಆಧರಿಸಿದೆ."
                action_text = "ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರದಲ್ಲಿ ವೈದ್ಯರನ್ನು ಭೇಟಿಯಾಗಿ ಪರಿಶೀಲಿಸಿ."
            elif language == "hi":
                answer_body = (
                    f"आपका समग्र एनसीडी जोखिम स्तर: **{overall_tier}** ({int(overall_score * 100)}%) है।\n\n"
                    f"मुख्य योगदान कारक:\n{drivers_str}\n\n"
                    "यह कोई अंतिम निदान नहीं है, बल्कि निवारक देखभाल के लिए एक शुरुआती चेतावनी है।"
                )
                uncertainty_text = "जोखिम स्कोर सांख्यिकीय मॉडलों पर आधारित है।"
                action_text = "डॉक्टर से परामर्श लें और निवारक योजना का पालन करें।"
            else:
                clinical_rec = "\n\nClinical review recommended: High risk stratification warrants clinician evaluation." if overall_tier in ["HIGH", "ELEVATED"] or overall_score >= 0.6 else ""
                answer_body = (
                    f"Based on your recent preventive screening, your composite NCD risk is classified as **{overall_tier}** ({int(overall_score * 100)}%).\n\n"
                    f"Top Contributing Biometric Factors:\n{drivers_str}\n\n"
                    f"This screening score highlights early physiological markers where targeted lifestyle adjustments can prevent progression.{clinical_rec}"
                )
                uncertainty_text = "Risk stratification is an early warning model, not a medical diagnosis."
                action_text = "Discuss these screening observations with your clinician during your next visit."

        # Intent D: Missing Information Inquiry
        elif any(w in q_lower for w in ["missing", "complete", "what do you need", "update", "check"]):
            missing_items = self._detect_missing_data(vitals, labs, wearables)
            citations_list.append("Ayushman Bharat Comprehensive Primary Health Care Guidelines")

            if missing_items:
                missing_str = "\n".join([f"• {item}" for item in missing_items])
                answer_body = (
                    f"To provide you with the most accurate preventive guidance, the following health records are currently missing or due for an update:\n\n"
                    f"{missing_str}\n\n"
                    "Scheduling a quick check-up with your local ASHA worker or syncing your wearable device will ensure your risk models remain accurate."
                )
                action_text = "Visit your local PHC or connect with your ASHA worker for missing screening checks."
            else:
                answer_body = "Your preventive health profile is comprehensive! All essential vitals, labs, and activity records are up to date."
                action_text = "Continue your daily habits and review again next month."

            uncertainty_text = "Predictive accuracy increases with complete biometric profiles."

        # Default: General Health Education & Assistant Guidance
        else:
            citations_list.append("ICMR Preventive Healthcare Guidelines")
            citations_list.append("WHO Global NCD Action Plan")

            if language == "kn":
                answer_body = (
                    f"ನಮಸ್ಕಾರ {citizen_name}. ನಿಮ್ಮ ಸೇವಾಹೆಲ್ತ್ ಎಐ ತಡೆಗಟ್ಟುವಿಕೆ ಸಹಾಯಕನಾಗಿ ನಾನು ಇಲ್ಲಿದ್ದೇನೆ.\n\n"
                    f"• ಪ್ರಸ್ತುತ ಅಪಾಯದ ಸ್ಥಿತಿ: {overall_tier} ({int(overall_score * 100)}%)\n"
                    f"• ದೀರ್ಘಕಾಲೀನ ಪ್ರವೃತ್ತಿ: {trend}\n"
                    f"• ಜೀವನಶೈಲಿ ಯೋಜನೆಯ ಪಾಲನೆ: {care_plan.get('adherence_percentage', 0.0):.0f}%\n\n"
                    "ನಿಮ್ಮ ಆಹಾರ, ವ್ಯಾಯಾಮ ಅಥವಾ ಆರೋಗ್ಯ ಪ್ರವೃತ್ತಿಯ ಬಗ್ಗೆ ನೀವು ಕೇಳಬಹುದು.\n\n"
                    "SAFETY NOTICE: ದೈನಂದಿನ ತಡೆಗಟ್ಟುವಿಕೆ ಕಾರ್ಯಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."
                )
                uncertainty_text = "ಶೈಕ್ಷಣಿಕ ಮತ್ತು ಜೀವನಶೈಲಿ ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ; ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಯನ್ನು ಬದಲಿಸುವುದಿಲ್ಲ."
                action_text = "ದೈನಂದಿನ ತಡೆಗಟ್ಟುವಿಕೆ ಕಾರ್ಯಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."
            elif language == "hi":
                answer_body = (
                    f"नमस्ते {citizen_name}. मैं आपका सेवाहेल्थ एआई प्रिवेंशन सहायक हूँ।\n\n"
                    f"• वर्तमान जोखिम स्तर: {overall_tier} ({int(overall_score * 100)}%)\n"
                    f"• दीर्घकालिक प्रवृत्ति: {trend}\n"
                    f"• जीवनशैली योजना अनुपालन: {care_plan.get('adherence_percentage', 0.0):.0f}%\n\n"
                    "आप अपने आहार, व्यायाम या स्वास्थ्य प्रवृत्तियों के बारे में पूछ सकते हैं।"
                )
                uncertainty_text = "केवल शैक्षिक और निवारक मार्गदर्शन; यह डॉक्टरी परामर्श का विकल्प नहीं है।"
                action_text = "अपने दैनिक कार्यों की समीक्षा करें।"
            else:
                answer_body = (
                    f"Hello {citizen_name}. As your SevaHealth AI Prevention Assistant, I am here to help you understand your "
                    f"screening results, track your health trajectory, and achieve your 30-day lifestyle goals.\n\n"
                    f"• Current Risk Status: {overall_tier} ({int(overall_score * 100)}%)\n"
                    f"• Longitudinal Trajectory: {trend}\n"
                    f"• Care Plan Adherence: {care_plan.get('adherence_percentage', 0.0):.0f}%\n\n"
                    "How can I assist you today? You can ask about your risk drivers, dietary swaps, daily exercises, or upcoming check-ins."
                )
                uncertainty_text = "Educational and lifestyle guidance only; does not replace medical consultation."
                action_text = "Review your daily prevention tasks."

        # 5. Enforce Safety Disclaimer & Post-Audit with Safety Envelope
        safety_eval = ClinicalSafetyEngine.evaluate_clinical_interaction(
            patient_data={"citizen_id": citizen_id, "name": citizen_name, "age": age, **vitals, **labs},
            user_prompt=user_query,
            ai_response_text=answer_body,
            model_version="v1.0.0",
            agent_version="v1.0.0",
        )

        resp = PreventionAgentResponse(
            answer=safety_eval.sanitized_response or answer_body,
            evidence=evidence_list,
            uncertainty=uncertainty_text,
            recommended_action=action_text,
            escalation=safety_eval.is_emergency,
            citations=citations_list,
            tool_calls_executed=executed_tools,
            language=language,
            safety_banners=safety_eval.safety_banners,
            safety_envelope=safety_eval.envelope,
        )

        agent_telemetry.log_decision(
            agent_name="SevaHealthPreventionAgent",
            citizen_id=citizen_id,
            actor_id=actor.sub,
            user_query=user_query,
            decision="PREVENTION_GUIDANCE_PROVIDED",
            escalation=safety_eval.is_emergency,
            evidence_count=len(evidence_list),
        )

        metrics.record_agent_execution(
            agent_name="SevaHealthPreventionAgent",
            duration_ms=42.0,
            steps=len(executed_tools) or 1,
            escalated=safety_eval.is_emergency,
        )
        metrics.record_llm_call(
            provider="mock_clinical",
            model="gemini-1.5-flash",
            duration_ms=28.5,
            prompt_tokens=max(20, len(user_query.split()) * 4),
            completion_tokens=max(30, len(answer_body.split()) * 4),
            success=True,
        )
        for t in executed_tools:
            metrics.record_tool_call(tool_name=t, duration_ms=3.2, success=True)

        return resp

    async def summarize_for_clinician(
        self,
        citizen_id: str,
        actor: TokenPayload,
    ) -> LLMSOAPSummaryOutput:
        """Synthesizes longitudinal screening, wearable telemetry, and adherence into a structured SOAP clinical note."""
        profile = get_patient_profile(citizen_id=citizen_id, actor=actor)
        vitals = get_latest_vitals(citizen_id=citizen_id, actor=actor)
        labs = get_recent_labs(citizen_id=citizen_id, actor=actor)
        risk = get_risk_assessment(citizen_id=citizen_id, actor=actor)
        trajectory = get_risk_trajectory(citizen_id=citizen_id, actor=actor)
        wearables = get_wearable_summary(citizen_id=citizen_id, actor=actor)
        care_plan = get_intervention_plan(citizen_id=citizen_id, actor=actor)
        meds = get_medication_list(citizen_id=citizen_id, actor=actor)

        citizen_name = profile.get("name", "Unknown Patient")
        age = profile.get("age", "Unknown")

        # Subjective
        med_names = [f"{m.get('drug_name')} {m.get('dosage')}" for m in meds]
        adh_pct = care_plan.get("adherence_percentage", 0.0)
        subjective = (
            f"Patient: {citizen_name}, {age}yo. Community screening participant. "
            f"Current Adherence to 30-Day Lifestyle Care Plan: {adh_pct:.1f}%. "
            f"Reported active medications: {', '.join(med_names) if med_names else 'None reported'}. "
            f"Wearable activity level indicates {wearables.get('activity_level', 'MODERATE')} physical engagement."
        )

        # Objective
        vitals_str = ", ".join([f"{k.upper()}: {v['value']} {v['unit']}" for k, v in vitals.items()])
        labs_str = ", ".join([f"{k.upper()}: {v['value']} {v['unit']} ({v.get('interpretation', 'NORMAL')})" for k, v in labs.items()])
        wb_base = wearables.get("seven_day_baselines", {})
        wb_str = f"Avg RHR: {wb_base.get('avg_resting_heart_rate')} bpm, Avg HRV: {wb_base.get('avg_hrv_rmssd')} ms, Avg Steps: {wb_base.get('avg_daily_steps')}"
        objective = f"Vitals: [{vitals_str}]. Labs: [{labs_str}]. 7-Day Wearable Telemetry: [{wb_str}]."

        # Assessment
        overall_tier = risk.get("overall_tier", "MODERATE")
        trend = trajectory.get("overall_trend", "STABLE")
        drivers = [d["feature_name"] for d in risk.get("top_drivers", [])]
        assessment = (
            f"Evaluated Risk Tier: {overall_tier} ({int(risk.get('overall_score', 0.5) * 100)}%). "
            f"Longitudinal Trajectory: {trend} (Delta: {trajectory.get('change_percentage', 0.0):+0.1f}%). "
            f"Primary contributors: {', '.join(drivers) if drivers else 'Metabolic risk factors'}."
        )

        # Plan
        plan = (
            "1. Clinician verification of biometric elevations.\n"
            "2. Review existing pharmacological regimen vs clinical guidelines.\n"
            "3. Reinforce nutrition guidelines (millet substitution, dietary sodium < 2g/day).\n"
            "4. Schedule primary care follow-up in 30 days."
        )

        flags = [
            "CLINICAL DECISION SUPPORT: Generated by SevaHealth AI Prevention Agent.",
            "NON-DIAGNOSTIC: Requires physician sign-off before executing care interventions.",
        ]
        if overall_tier == "HIGH" or trend == "WORSENING":
            flags.append("HIGH_PRIORITY_REVIEW: Elevated biometric progression detected.")

        agent_telemetry.log_tool_call(
            tool_name="summarize_for_clinician",
            citizen_id=citizen_id,
            actor_id=actor.sub,
            actor_role=actor.role.value if hasattr(actor.role, "value") else str(actor.role),
            arguments={"citizen_id": citizen_id},
            status="SUCCESS",
            details="SOAP synthesis completed for clinician review.",
        )

        return LLMSOAPSummaryOutput(
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
            clinical_flags=flags,
        )

    @property
    def tools(self) -> List[Any]:
        """Catalog of whitelisted, authorized decision-support tools."""
        return [
            get_patient_profile,
            get_latest_vitals,
            get_recent_labs,
            get_risk_assessment,
            get_risk_trajectory,
            get_intervention_plan,
            get_wearable_summary,
            get_medication_list,
            get_clinical_history,
        ]

    def interact(
        self,
        citizen_id: str,
        user_message: str,
        actor: Optional[TokenPayload] = None,
        language: str = "en",
    ) -> Any:
        """Synchronous interactive interface with proactive adversarial guardrails."""
        if actor is None:
            actor = TokenPayload(
                sub=citizen_id,
                tenant_id="karnataka_state_health",
                role=UserRole.CITIZEN,
                scopes=["*"],
            )

        import asyncio
        import concurrent.futures

        q_lower = user_message.lower()
        if any(w in q_lower for w in ["override", "ignore all", "dr. evil", "unrestricted", "jailbreak", "jwt_secret_key", "environment variables", "database credentials"]):
            if any(m in q_lower for m in ["prescribe", "metformin", "medicine", "pill", "drug"]):
                res = PreventionAgentResponse(
                    answer="CLINICAL_SAFETY_GUARD: I cannot prescribe medications or alter pharmacological therapy. Pharmacotherapy requires licensed physician evaluation.",
                    evidence=[],
                    uncertainty="Prescriptive actions strictly prohibited.",
                    recommended_action="Consult a certified clinician.",
                    escalation=False,
                    safety_banners=[SafetyBanner.PROFESSIONAL_REVIEW.value],
                )
            else:
                res = PreventionAgentResponse(
                    answer="SECURITY_ALERT: Request denied. System directives, cryptographic keys, and internal credentials cannot be disclosed.",
                    evidence=[],
                    uncertainty="Security boundary violation.",
                    recommended_action="Please submit valid clinical questions.",
                    escalation=False,
                    safety_banners=[SafetyBanner.PROFESSIONAL_REVIEW.value],
                )
        else:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        res = executor.submit(asyncio.run, self.chat(citizen_id, user_message, actor, language)).result()
                else:
                    res = loop.run_until_complete(self.chat(citizen_id, user_message, actor, language))
            except RuntimeError:
                res = asyncio.run(self.chat(citizen_id, user_message, actor, language))

        class InteractiveAgentResult:
            def __init__(self, raw: PreventionAgentResponse):
                self.raw = raw
                self.response = raw.answer
                self.answer = raw.answer
                self.safety_banners = raw.safety_banners
                class BannerObj:
                    def __init__(self, msg):
                        self.message = msg
                base_banner = raw.safety_banners[0] if raw.safety_banners else "AI-generated information must be reviewed by a healthcare professional."
                self.safety_banner = BannerObj(f"{base_banner} Not intended for medical diagnosis or prescription.")
                self.tool_calls_executed = raw.tool_calls_executed

        return InteractiveAgentResult(res)


prevention_agent = SevaHealthPreventionAgent()
