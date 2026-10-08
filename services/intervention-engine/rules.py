from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field
import uuid

from services.intervention_engine.models import (
    InterventionCategory,
    PriorityRank,
    PrioritizedAction,
    SMARTGoal,
    EducationalModule,
    MeasurementSchedule,
    FollowUpEvent,
    ScheduledReminder,
)


class InterventionRule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: InterventionCategory
    priority_level: PriorityRank
    is_active: bool = True
    
    # Matching Criteria
    risk_domain_triggers: List[str] = []      # e.g., ["diabetes", "metabolic"]
    risk_tier_triggers: List[str] = []        # e.g., ["MODERATE", "HIGH", "CRITICAL"]
    trajectory_triggers: List[str] = []       # e.g., ["WORSENING"]
    lifestyle_triggers: List[str] = []        # e.g., ["SMOKER", "SEDENTARY", "POOR_SLEEP"]
    
    # Generated Artifact Factories
    action_title: str
    action_description: str
    frequency: str
    target_metric: Optional[str] = None
    evidence_citation: str
    expected_benefit_score: float = 0.85
    
    # Constraint Adaptation
    contraindicated_constraints: List[str] = [] # e.g. ["KNEE_OSTEOARTHRITIS", "JOINT_PAIN"]
    alternative_action_title: Optional[str] = None
    alternative_description: Optional[str] = None
    
    # Educational & Monitoring Pairings
    educational_module_title: Optional[str] = None
    educational_takeaway: Optional[str] = None
    cultural_adaptation: Optional[str] = None
    
    measurement_biometric: Optional[str] = None
    measurement_frequency: Optional[str] = None
    measurement_target: Optional[str] = None
    measurement_instructions: Optional[str] = None
    
    reminder_title: Optional[str] = None
    reminder_time: str = "08:00 AM"
    reminder_message: Optional[str] = None


class ConfigurableRuleRegistry:
    """Manages configurable intervention rules supporting evidence-based personalization."""
    
    def __init__(self):
        self._rules: Dict[str, InterventionRule] = {}
        self._load_default_rules()

    def register_rule(self, rule: InterventionRule):
        self._rules[rule.id] = rule

    def get_rule(self, rule_id: str) -> Optional[InterventionRule]:
        return self._rules.get(rule_id)

    def list_rules(self) -> List[InterventionRule]:
        return list(self._rules.values())

    def update_rule_status(self, rule_id: str, is_active: bool) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].is_active = is_active
            return True
        return False

    def _load_default_rules(self):
        default_rules = [
            # 1. NUTRITION: Glycemic Stabilization (Evidence: ICMR-NIN 2024 / ADA)
            InterventionRule(
                id="rule-nutri-millet",
                name="Traditional Millet Substitution for Glycemic Control",
                category=InterventionCategory.NUTRITION,
                priority_level=PriorityRank.EVIDENCE,
                risk_domain_triggers=["diabetes", "metabolic"],
                risk_tier_triggers=["MODERATE", "HIGH", "CRITICAL"],
                action_title="Swap 50% Refined Grains for Traditional Whole Millets",
                action_description="Replace white polished rice or refined flour with foxtail millet, ragi, or jowar. High dietary fiber slows carbohydrate digestion.",
                frequency="Daily at lunch or dinner",
                target_metric="1 serving whole millet",
                evidence_citation="ICMR-NIN Dietary Guidelines for Indians 2024; Anjana RM et al. ICMR-INDIAB",
                expected_benefit_score=0.88,
                educational_module_title="The Power of Ancient Millets for Blood Sugar Regulation",
                educational_takeaway="Whole millets have a lower glycemic index (54-60) compared to polished white rice (78), flattening post-meal glucose spikes.",
                cultural_adaptation="Traditional Karnataka Ragi Mudde or Foxtail Millet Pongal prepared with vegetables.",
                measurement_biometric="FASTING_GLUCOSE",
                measurement_frequency="Day 1, 15, and 30",
                measurement_target="< 100 mg/dL",
                measurement_instructions="Measure before breakfast using point-of-care glucometer or PHC lab assay.",
                reminder_title="Lunch Plate Check",
                reminder_time="12:30 PM",
                reminder_message="Remember your millet serving today: half your plate vegetables, one-quarter millet!",
            ),

            # 2. NUTRITION: Dietary Sodium Reduction (Evidence: WHO / ACC/AHA)
            InterventionRule(
                id="rule-nutri-sodium",
                name="Dietary Sodium Restriction for Vascular Protection",
                category=InterventionCategory.NUTRITION,
                priority_level=PriorityRank.EVIDENCE,
                risk_domain_triggers=["hypertension", "cardiovascular"],
                risk_tier_triggers=["MODERATE", "HIGH", "CRITICAL"],
                action_title="Limit Added Salt and Eliminate Salted Pickles/Papad",
                action_description="Restrict daily table salt to under 1 level teaspoon (< 5g salt / < 2g sodium). Substitute flavor with lemon, amla, curry leaves, and cumin.",
                frequency="Daily with all meals",
                target_metric="< 1 level tsp salt daily",
                evidence_citation="WHO Global Sodium Reduction Benchmarks 2021; ACC/AHA 2017 Guidelines",
                expected_benefit_score=0.85,
                educational_module_title="Hidden Sodium in Indian Diets: Papad, Pickles, and Chutneys",
                educational_takeaway="Up to 40% of dietary sodium in Indian meals comes from preserved side accompaniments rather than cooking salt.",
                cultural_adaptation="Use freshly squeezed lemon juice, crushed ginger, and roasted cumin seeds to enhance flavor without salt.",
                measurement_biometric="BLOOD_PRESSURE",
                measurement_frequency="Weekly on Sunday mornings",
                measurement_target="< 120/80 mmHg",
                measurement_instructions="Measure seated with arm at heart level after 5 minutes of quiet rest.",
                reminder_title="Low-Sodium Seasoning Reminder",
                reminder_time="10:30 AM",
                reminder_message="Cooking tip: Enhance vegetable flavors with lemon and fresh herbs instead of added table salt.",
            ),

            # 3. PHYSICAL ACTIVITY: Post-Meal Walking (Evidence: Reynolds et al., Diabetologia)
            InterventionRule(
                id="rule-act-postprandial",
                name="Post-Prandial Glycemic Walking Routine",
                category=InterventionCategory.PHYSICAL_ACTIVITY,
                priority_level=PriorityRank.EXPECTED_BENEFIT,
                risk_domain_triggers=["diabetes", "metabolic", "obesity"],
                risk_tier_triggers=["MODERATE", "HIGH", "CRITICAL"],
                action_title="15-Minute Post-Dinner Brisk Walk",
                action_description="Take a relaxed brisk walk within 30 minutes after completing your evening meal to stimulate GLUT-4 glucose uptake.",
                frequency="Daily within 30 min post-dinner",
                target_metric="15 minutes / 1,800 steps",
                evidence_citation="Reynolds AN et al. Advice to walk after meals reduces postprandial glycemia. Diabetologia 2016.",
                expected_benefit_score=0.90,
                contraindicated_constraints=["KNEE_OSTEOARTHRITIS", "JOINT_PAIN", "SEVERE_MOBILITY_LIMITATION"],
                alternative_action_title="15-Minute Seated Upper-Body Dynamic Movement & Arm Circles",
                alternative_description="Safe non-impact seated movement protects knee joints while still activating skeletal muscle glucose clearance.",
                educational_module_title="Why Walking Immediately After Eating Lowers Blood Sugar",
                educational_takeaway="Active leg muscles absorb circulating glucose directly without requiring excess pancreatic insulin release.",
                cultural_adaptation="Evening stroll in local community park or courtyard ('Shatapavali').",
                reminder_title="Evening Stroll Time",
                reminder_time="08:45 PM",
                reminder_message="Dinner finished? Take your 15-minute gentle stroll to balance your evening glucose.",
            ),

            # 4. PHYSICAL ACTIVITY: Joint-Safe Aerobic Conditioning (Evidence: American College of Sports Medicine)
            InterventionRule(
                id="rule-act-aerobic",
                name="Progressive Aerobic Activity & Step Target",
                category=InterventionCategory.PHYSICAL_ACTIVITY,
                priority_level=PriorityRank.SAFETY,
                risk_domain_triggers=["cardiovascular", "hypertension", "obesity"],
                risk_tier_triggers=["LOW", "MODERATE", "HIGH"],
                action_title="Progressive 30-Minute Aerobic Conditioning",
                action_description="Target 7,500 to 10,000 steps daily or 30 minutes of continuous moderate movement 5 days per week.",
                frequency="5 days per week",
                target_metric="30 minutes / 8,000 steps daily",
                evidence_citation="WHO Physical Activity and Sedentary Behaviour Guidelines 2020",
                expected_benefit_score=0.82,
                contraindicated_constraints=["KNEE_OSTEOARTHRITIS", "ARTHRITIS", "FRAILTY"],
                alternative_action_title="Gentle Chair Yoga and Restorative Stretching",
                alternative_description="Perform low-impact chair asanas (Tadasana, Marjaryasana seated) to preserve joint flexibility without articular compression.",
                educational_module_title="Building Cardiovascular Endurance Safely",
                educational_takeaway="Consistent moderate walking lowers systolic blood pressure by an average of 5-8 mmHg over 4-6 weeks.",
                cultural_adaptation="Utilize morning temple walks or municipal walking track with walking companions.",
                reminder_title="Morning Activity Window",
                reminder_time="06:30 AM",
                reminder_message="Start your morning with a brisk 20-minute movement routine in fresh air.",
            ),

            # 5. SLEEP: Circadian Rhythm & Sleep Hygiene (Evidence: Sleep Research Society)
            InterventionRule(
                id="rule-sleep-circadian",
                name="Circadian Screen Sunset & Sleep Regularity",
                category=InterventionCategory.SLEEP,
                priority_level=PriorityRank.FEASIBILITY,
                risk_domain_triggers=["metabolic", "hypertension", "lifestyle"],
                lifestyle_triggers=["POOR_SLEEP", "SHORT_SLEEP"],
                action_title="Circadian Screen Sunset (45-Minute Pre-Bed Digital Detox)",
                action_description="Turn off smartphones, tablets, and television screens 45 minutes before sleep to enable natural melatonin secretion.",
                frequency="Daily 45 min before sleep",
                target_metric="7.5 hours sleep with screens off 45 min prior",
                evidence_citation="Consensus Statement of the American Academy of Sleep Medicine and Sleep Research Society",
                expected_benefit_score=0.78,
                educational_module_title="How Sleep Deprivation Increases Cortisol and Blood Pressure",
                educational_takeaway="Sleeping under 6 hours raises nocturnal sympathetic activity and increases morning systolic blood pressure surges.",
                cultural_adaptation="Replace late-night phone browsing with soothing instrumental Indian classical music or prayer.",
                reminder_title="Digital Sunset Wind-Down",
                reminder_time="09:45 PM",
                reminder_message="Time to power down mobile screens. Relax your eyes and prepare for deep restorative sleep.",
            ),

            # 6. WEIGHT MANAGEMENT: Visceral Adiposity & Portion Plate (Evidence: ICMR / Misra et al.)
            InterventionRule(
                id="rule-weight-portion",
                name="Portion Plate Calibration for Central Obesity",
                category=InterventionCategory.WEIGHT_MANAGEMENT,
                priority_level=PriorityRank.EXPECTED_BENEFIT,
                risk_domain_triggers=["obesity", "metabolic"],
                risk_tier_triggers=["MODERATE", "HIGH", "CRITICAL"],
                action_title="Adopt the 2:1:1 Half-Plate Fiber Rule",
                action_description="Fill half your plate with raw/cooked green vegetables, one-quarter with lean protein (dal, sprouts, curd, egg), and one-quarter with complex grains.",
                frequency="Daily lunch and dinner",
                target_metric="Half plate vegetables at every major meal",
                evidence_citation="Misra A et al. Consensus Dietary Guidelines for Asian Indians; J Assoc Physicians India 2009",
                expected_benefit_score=0.86,
                educational_module_title="The Thin-Fat Indian Phenotype and Waist-to-Height Ratio",
                educational_takeaway="In Asian Indians, abdominal fat around organs is far more dangerous than subcutaneous fat. Your waist circumference should be less than half your height.",
                cultural_adaptation="Include locally available greens such as methi, palak, drumstick leaves, and cucumber.",
                measurement_biometric="WAIST_CIRCUMFERENCE",
                measurement_frequency="Every 15 days",
                measurement_target="< 90 cm (Men), < 80 cm (Women)",
                measurement_instructions="Measure midway between the lowest rib and top of iliac crest at the end of normal expiration.",
                reminder_title="Meal Plate Check",
                reminder_time="01:00 PM",
                reminder_message="Before serving: is half your plate vibrant vegetables and fresh green salad?",
            ),

            # 7. SMOKING CESSATION: 5D Craving Delay Technique (Evidence: WHO / CDC)
            InterventionRule(
                id="rule-smoke-cessation",
                name="Tobacco Craving Interception & 5D Strategy",
                category=InterventionCategory.SMOKING_CESSATION,
                priority_level=PriorityRank.SAFETY,
                risk_domain_triggers=["cardiovascular", "hypertension"],
                lifestyle_triggers=["SMOKER", "TOBACCO_USER"],
                action_title="Implement the 5D Tobacco Craving Interception Protocol",
                action_description="When craving strikes, execute the 5Ds: Delay 5 minutes, Deep breathe, Drink a glass of cold water, Distract with an activity, Discuss with a support partner.",
                frequency="On demand whenever craving occurs",
                target_metric="Zero tobacco consumption",
                evidence_citation="WHO Tobacco Free Initiative Guidelines for Controlling and Monitoring the Tobacco Epidemic",
                expected_benefit_score=0.95,
                educational_module_title="Cardiovascular Healing Timeline After Tobacco Cessation",
                educational_takeaway="Within 24 hours of tobacco cessation, coronary vasoconstriction subsides and arterial endothelial function begins immediate repair.",
                cultural_adaptation="Keep roasted fennel seeds (saunf) and cardamom pods on hand as natural oral substitutes.",
                reminder_title="Smoke-Free Commitment Check",
                reminder_time="09:00 AM",
                reminder_message="Stay committed to your smoke-free journey today. Each craving lasts only 3-5 minutes!",
            ),

            # 8. ALCOHOL REDUCTION: Zero-Alcohol Windows (Evidence: WHO / NIAAA)
            InterventionRule(
                id="rule-alcohol-reduction",
                name="Alcohol Moderation and Zero-Alcohol Weekday Protocol",
                category=InterventionCategory.ALCOHOL_REDUCTION,
                priority_level=PriorityRank.SAFETY,
                risk_domain_triggers=["hypertension", "metabolic"],
                lifestyle_triggers=["ALCOHOL_CONSUMER"],
                action_title="Establish 4 Consecutive Zero-Alcohol Days Per Week",
                action_description="Protect hepatic detoxification and nocturnal heart rate by strictly abstaining from alcohol Monday through Thursday.",
                frequency="4 consecutive alcohol-free days weekly",
                target_metric="Zero standard drinks on target days",
                evidence_citation="WHO Global Strategy to Reduce the Harmful Use of Alcohol; UK Chief Medical Officers' Low Risk Drinking Guidelines",
                expected_benefit_score=0.84,
                educational_module_title="Alcohol's Impact on Blood Pressure and Deep REM Sleep",
                educational_takeaway="Even moderate alcohol suppresses restorative deep sleep and elevates next-morning vascular systolic resistance.",
                cultural_adaptation="Substitute evening social drinks with spiced buttermilk (chaas) or fresh tender coconut water.",
                reminder_title="Alcohol-Free Evening Choice",
                reminder_time="07:00 PM",
                reminder_message="Choose a refreshing mint chaas or lime soda tonight. Your heart and liver will thank you!",
            ),

            # 9. STRESS MANAGEMENT: Vagal Tone & Pranayama (Evidence: NIH / Harvard Health)
            InterventionRule(
                id="rule-stress-vagal",
                name="Diaphragmatic Pranayama & Autonomic Regulation",
                category=InterventionCategory.STRESS_MANAGEMENT,
                priority_level=PriorityRank.EVIDENCE,
                risk_domain_triggers=["hypertension", "cardiovascular", "lifestyle"],
                action_title="10-Minute Slow Diaphragmatic Breathing (Anulom Vilom / 4-7-8)",
                action_description="Engage in 10 minutes of slow alternate nostril breathing twice daily. Activates the parasympathetic vagal brake to lower heart rate and blood pressure.",
                frequency="Twice daily (Morning & Evening)",
                target_metric="10 minutes morning, 10 minutes evening",
                evidence_citation="Jerath R et al. Physiology of long pranayamic breathing: neural respiratory elements may provide a mechanism. Med Hypotheses 2006",
                expected_benefit_score=0.82,
                educational_module_title="Activating the Vagus Nerve to Lower Blood Pressure",
                educational_takeaway="Slow breathing at 6 breaths per minute optimizes baroreflex sensitivity and significantly increases Heart Rate Variability (HRV).",
                cultural_adaptation="Traditional Patanjali pranayama practice in peaceful home prayer or meditation space.",
                reminder_title="Mindful Breath Break",
                reminder_time="05:30 PM",
                reminder_message="Pause your busy day for 5-10 minutes of slow, calming diaphragmatic breaths.",
            ),

            # 10. SCREENING ADHERENCE: Midpoint Reassessment (Evidence: National NCD Guidelines)
            InterventionRule(
                id="rule-screen-adherence",
                name="Day-15 Biometric Progress Review",
                category=InterventionCategory.SCREENING_ADHERENCE,
                priority_level=PriorityRank.PREFERENCE,
                risk_domain_triggers=["diabetes", "hypertension", "obesity"],
                action_title="Conduct Midpoint 15-Day Biometric Milestone Assessment",
                action_description="Record updated blood pressure, body weight, and morning fasting glucose to evaluate care plan response.",
                frequency="Day 15 of 30-day plan",
                target_metric="Complete 3 biometric measurements on Day 15",
                evidence_citation="Operational Guidelines for Prevention, Screening, and Control of Common NCDs; Ministry of Health & Family Welfare",
                expected_benefit_score=0.75,
                educational_module_title="Why Tracking Numbers Drives Long-Term Habit Formation",
                educational_takeaway="Citizens who track vital biomarkers every two weeks achieve 42% higher 90-day lifestyle adherence.",
                cultural_adaptation="Health worker or family member assists with point-of-care recording.",
                reminder_title="Midpoint Milestone Check-In",
                reminder_time="08:00 AM",
                reminder_message="Day 15 milestone reached! Record your blood pressure and fasting glucose today.",
            ),

            # 11. CLINICAL FOLLOW-UP: Human-in-the-Loop Primary Care (Evidence: WHO Package of Essential NCD Interventions)
            InterventionRule(
                id="rule-clinical-followup",
                name="Frontline Health Worker & Clinician Coordination",
                category=InterventionCategory.CLINICAL_FOLLOWUP,
                priority_level=PriorityRank.SAFETY,
                risk_domain_triggers=["diabetes", "hypertension", "renal"],
                risk_tier_triggers=["HIGH", "CRITICAL"],
                trajectory_triggers=["WORSENING"],
                action_title="Schedule Frontline ASHA Home Check & Clinician Tele-Review",
                action_description="Connect with your assigned ASHA worker and primary care physician to review progress, verify safety, and discuss prescription needs.",
                frequency="Day 7 (ASHA) and Day 30 (Physician)",
                target_metric="Attend 2 scheduled clinical follow-up sessions",
                evidence_citation="WHO Package of Essential Noncommunicable (PEN) Disease Interventions for Primary Health Care",
                expected_benefit_score=0.92,
                educational_module_title="Collaborative Care: You and Your Primary Healthcare Team",
                educational_takeaway="Preventive care works best when lifestyle modifications are shared with and supervised by your clinical team.",
                cultural_adaptation="Coordinated through your local Ayushman Bharat Health and Wellness Centre (AB-HWC).",
                reminder_title="Clinical Visit Schedule Reminder",
                reminder_time="09:00 AM",
                reminder_message="Reminder: Your ASHA worker check-in is scheduled this week. Keep your recent vitals log ready.",
            ),
        ]

        for r in default_rules:
            self._rules[r.id] = r


# Global singleton instance
rule_registry = ConfigurableRuleRegistry()
