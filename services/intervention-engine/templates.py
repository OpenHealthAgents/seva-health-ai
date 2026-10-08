from typing import List, Dict, Any
from pydantic import BaseModel, Field

from services.intervention_engine.models import (
    InterventionCategory,
    PriorityRank,
    SMARTGoal,
    MeasurementSchedule,
    FollowUpEvent,
)


class PreventionTemplate(BaseModel):
    template_id: str
    name: str
    target_domain: str
    target_risk_tier: str
    description: str
    goals: List[SMARTGoal] = []
    recommended_rules: List[str] = []
    standard_measurements: List[MeasurementSchedule] = []
    standard_followups: List[FollowUpEvent] = []


PREVENTION_TEMPLATES: Dict[str, PreventionTemplate] = {
    "prediabetes_reversal": PreventionTemplate(
        template_id="prediabetes_reversal",
        name="Pre-Diabetes Glycemic Stabilization & Reversal",
        target_domain="diabetes",
        target_risk_tier="HIGH",
        description="Targeted 30-day glycemic modulation designed to blunt insulin excursions, promote post-prandial muscular glucose disposal, and halt progression toward Type 2 Diabetes.",
        goals=[
            SMARTGoal(
                pillar=InterventionCategory.NUTRITION,
                title="Shift to Low-Glycemic Whole Millets",
                target_metric="Replace 50% white polished rice with foxtail millet, ragi, or jowar daily",
                timeline_days=30,
                clinical_rationale="Whole millets contain soluble fiber that attenuates post-prandial glycemic spikes.",
            ),
            SMARTGoal(
                pillar=InterventionCategory.PHYSICAL_ACTIVITY,
                title="Post-Meal Glucose Disposal Movement",
                target_metric="15-minute brisk walk within 30 minutes of dinner, 6 days per week",
                timeline_days=30,
                clinical_rationale="Activates insulin-independent GLUT-4 translocation in skeletal muscle.",
            ),
            SMARTGoal(
                pillar=InterventionCategory.WEIGHT_MANAGEMENT,
                title="Central Adiposity Waist Management",
                target_metric="Achieve 1.5 cm reduction in waist circumference over 30 days",
                timeline_days=30,
                clinical_rationale="Reduces ectopic visceral adipose fat, the primary driver of hepatic insulin resistance in Asian Indians.",
            ),
        ],
        recommended_rules=["rule-nutri-millet", "rule-act-postprandial", "rule-weight-portion", "rule-screen-adherence", "rule-clinical-followup"],
        standard_measurements=[
            MeasurementSchedule(
                biometric="FASTING_GLUCOSE",
                frequency="Day 1, 15, and 30",
                target_range="< 100 mg/dL",
                instructions="Measure after 8 hours of overnight fasting using a standard capillary glucometer.",
            ),
            MeasurementSchedule(
                biometric="WAIST_CIRCUMFERENCE",
                frequency="Day 1 and Day 30",
                target_range="< 90 cm (Men), < 80 cm (Women)",
                instructions="Measure at midpoint between lowest rib and iliac crest after gentle exhalation.",
            ),
        ],
        standard_followups=[
            FollowUpEvent(
                day_number=7,
                provider_role="ASHA_WORKER",
                channel="HOME_VISIT",
                agenda="Review millet dietary transition, address gastrointestinal tolerance, inspect post-meal walk habit.",
            ),
            FollowUpEvent(
                day_number=30,
                provider_role="CLINICIAN",
                channel="PHC_VISIT",
                agenda="Evaluate 30-day glycemic response, review repeat fasting glucose, discuss long-term maintenance.",
            ),
        ],
    ),

    "hypertension_vascular": PreventionTemplate(
        template_id="hypertension_vascular",
        name="Hypertension Sodium-Calibrated Vascular Protection",
        target_domain="hypertension",
        target_risk_tier="HIGH",
        description="Comprehensive vascular decompression plan targeting dietary sodium reduction, vagal parasympathetic activation, and continuous blood pressure logging.",
        goals=[
            SMARTGoal(
                pillar=InterventionCategory.NUTRITION,
                title="Strict Dietary Sodium Restriction",
                target_metric="Limit total daily added salt to < 1 level teaspoon (< 5g salt / < 2g sodium)",
                timeline_days=30,
                clinical_rationale="Directly reduces extracellular fluid volume and systemic vascular resistance.",
            ),
            SMARTGoal(
                pillar=InterventionCategory.STRESS_MANAGEMENT,
                title="Autonomic Vagal Nerve Stimulation",
                target_metric="10 minutes slow diaphragmatic breathing (pranayama) twice daily",
                timeline_days=30,
                clinical_rationale="Optimizes baroreflex sensitivity and dampens sympathetic adrenergic drive.",
            ),
            SMARTGoal(
                pillar=InterventionCategory.SCREENING_ADHERENCE,
                title="Weekly Blood Pressure Documentation",
                target_metric="Record resting seated blood pressure every Sunday morning",
                timeline_days=30,
                clinical_rationale="Tracks vascular response curve and prevents undetected hypertensive spikes.",
            ),
        ],
        recommended_rules=["rule-nutri-sodium", "rule-act-aerobic", "rule-stress-vagal", "rule-alcohol-reduction", "rule-clinical-followup"],
        standard_measurements=[
            MeasurementSchedule(
                biometric="BLOOD_PRESSURE",
                frequency="Weekly on Sunday morning",
                target_range="< 120/80 mmHg",
                instructions="Sit quietly for 5 minutes without talking; take duplicate reading 2 minutes apart and average them.",
            ),
        ],
        standard_followups=[
            FollowUpEvent(
                day_number=14,
                provider_role="PRIMARY_CARE_NURSE",
                channel="TELE_CONSULT",
                agenda="Review weekly BP log, verify sodium reduction compliance, check for headaches/dizziness.",
            ),
            FollowUpEvent(
                day_number=30,
                provider_role="CLINICIAN",
                channel="PHC_VISIT",
                agenda="Comprehensive clinical evaluation, rule out secondary HTN or end-organ strain, evaluate medical therapy.",
            ),
        ],
    ),

    "cardiovascular_protection": PreventionTemplate(
        template_id="cardiovascular_protection",
        name="Cardiovascular Atherosclerosis Prevention & Tobacco Freedom",
        target_domain="cardiovascular",
        target_risk_tier="HIGH",
        description="Multi-factor primary prevention program targeting coronary endothelial recovery, atherogenic dyslipidemia reduction, and tobacco cessation.",
        goals=[
            SMARTGoal(
                pillar=InterventionCategory.SMOKING_CESSATION,
                title="Complete Tobacco Cessation Commitment",
                target_metric="Zero cigarettes, bidis, or gutkha sachets throughout the 30-day journey",
                timeline_days=30,
                clinical_rationale="Halts direct chemical endothelial injury and coronary vasoconstriction immediately.",
            ),
            SMARTGoal(
                pillar=InterventionCategory.PHYSICAL_ACTIVITY,
                title="Cardiorespiratory Aerobic Exercise",
                target_metric="150 minutes of moderate-intensity brisk walking per week",
                timeline_days=30,
                clinical_rationale="Increases high-density lipoprotein (HDL) and stimulates myocardial perfusion.",
            ),
        ],
        recommended_rules=["rule-smoke-cessation", "rule-nutri-sodium", "rule-act-aerobic", "rule-sleep-circadian", "rule-clinical-followup"],
        standard_measurements=[
            MeasurementSchedule(
                biometric="BLOOD_PRESSURE",
                frequency="Twice weekly",
                target_range="< 130/80 mmHg",
                instructions="Measure resting seated blood pressure at the same time each morning.",
            ),
        ],
        standard_followups=[
            FollowUpEvent(
                day_number=7,
                provider_role="ASHA_WORKER",
                channel="HOME_VISIT",
                agenda="Assess nicotine withdrawal symptoms, review 5D craving coping techniques, verify family support.",
            ),
            FollowUpEvent(
                day_number=30,
                provider_role="CLINICIAN",
                channel="PHC_VISIT",
                agenda="Comprehensive 10-year ASCVD recalculation and lipid panel review with Medical Officer.",
            ),
        ],
    ),

    "metabolic_weight_loss": PreventionTemplate(
        template_id="metabolic_weight_loss",
        name="Metabolic Health & Visceral Adiposity Reduction",
        target_domain="obesity",
        target_risk_tier="MODERATE",
        description="Nutritional and behavioral restructuring aimed at reducing abdominal adiposity, improving insulin sensitivity, and managing caloric density.",
        goals=[
            SMARTGoal(
                pillar=InterventionCategory.WEIGHT_MANAGEMENT,
                title="Adopt 2:1:1 Half-Plate Veggie Standard",
                target_metric="50% plate raw/cooked vegetables at lunch and dinner",
                timeline_days=30,
                clinical_rationale="Increases satiety via gastric stretch receptors and displaces high-calorie refined grains.",
            ),
            SMARTGoal(
                pillar=InterventionCategory.PHYSICAL_ACTIVITY,
                title="Daily Non-Exercise Activity Thermogenesis (NEAT)",
                target_metric="8,500 steps daily tracked via pedometer/wearable",
                timeline_days=30,
                clinical_rationale="Enhances daily energy expenditure and mitigates age-related metabolic slowing.",
            ),
        ],
        recommended_rules=["rule-weight-portion", "rule-act-aerobic", "rule-nutri-millet", "rule-sleep-circadian", "rule-screen-adherence"],
        standard_measurements=[
            MeasurementSchedule(
                biometric="BODY_WEIGHT",
                frequency="Weekly on Friday morning",
                target_range="Target -1.0 to -2.0 kg over 30 days",
                instructions="Weigh in fasting after morning voiding with light clothing.",
            ),
            MeasurementSchedule(
                biometric="WAIST_CIRCUMFERENCE",
                frequency="Day 1, 15, and 30",
                target_range="< 90 cm (Men), < 80 cm (Women)",
                instructions="Measure at horizontal level of belly button at the end of normal expiration.",
            ),
        ],
        standard_followups=[
            FollowUpEvent(
                day_number=15,
                provider_role="WELLNESS_COACH",
                channel="TELE_CONSULT",
                agenda="Evaluate portion control habits, check weight trajectory, adjust daily step target.",
            ),
        ],
    ),

    "renal_preservation": PreventionTemplate(
        template_id="renal_preservation",
        name="Renal Microvascular Preservation & Hydration Protocol",
        target_domain="renal",
        target_risk_tier="MODERATE",
        description="Preservation protocol designed to shield glomerular filtration from diabetic and hypertensive shear stress and prevent nephrotoxic exposures.",
        goals=[
            SMARTGoal(
                pillar=InterventionCategory.NUTRITION,
                title="Optimal Hydration and Salt Balance",
                target_metric="2.5 liters of clean water daily; sodium < 2g/day",
                timeline_days=30,
                clinical_rationale="Prevents renal hypoperfusion and reduces intraglomerular capillary hypertension.",
            ),
            SMARTGoal(
                pillar=InterventionCategory.CLINICAL_FOLLOWUP,
                title="Nephrotoxic Medication Avoidance",
                target_metric="Zero unprescribed over-the-counter painkiller (NSAID) consumption",
                timeline_days=30,
                clinical_rationale="NSAIDs cause afferent arteriolar constriction and precipitate acute-on-chronic renal decline.",
            ),
        ],
        recommended_rules=["rule-nutri-sodium", "rule-screen-adherence", "rule-clinical-followup"],
        standard_measurements=[
            MeasurementSchedule(
                biometric="BLOOD_PRESSURE",
                frequency="Twice weekly",
                target_range="< 120/80 mmHg (strict KDIGO target)",
                instructions="Seated bilateral resting measurement.",
            ),
        ],
        standard_followups=[
            FollowUpEvent(
                day_number=30,
                provider_role="CLINICIAN",
                channel="PHC_VISIT",
                agenda="Review repeat serum creatinine, eGFR, and spot urine albumin-to-creatinine ratio (uACR).",
            ),
        ],
    ),
}
