from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta, timezone
import uuid

from packages.types.enums import InterventionPillar
from packages.clinical_models.care_plan import DailyTask, CarePlan
from packages.clinical_models.risk import RiskAssessment
from services.intervention_engine.models import (
    InterventionCategory,
    PriorityRank,
    SMARTGoal,
    PrioritizedAction,
    ScheduledReminder,
    EducationalModule,
    MeasurementSchedule,
    FollowUpEvent,
    PreventionPlanInput,
    ComprehensivePreventionPlan,
)
from services.intervention_engine.rules import rule_registry, InterventionRule
from services.intervention_engine.templates import PREVENTION_TEMPLATES, PreventionTemplate


class PreventionInterventionEngine:
    """Core Prevention Intervention Decision Engine for SevaHealth AI.
    
    Synthesizes multi-source inputs (Risk Profile, Trajectory, Lifestyle, Goals,
    Preferences, Constraints, Community Resources, Clinician Recommendations)
    into a structured 30-day personalized preventive care plan.
    
    Strictly adheres to:
    1. 5-Tier Prioritization: Safety > Evidence > Expected Benefit > Feasibility > Patient Preference
    2. Non-Autonomous Medication Governance: Never prescribes or alters medication.
    3. Multi-Pillar Support: Nutrition, Physical Activity, Sleep, Weight, Smoking,
       Alcohol, Stress, Screening, and Clinical Follow-Up.
    """

    def generate_plan(
        self,
        plan_input: PreventionPlanInput,
        start_date: Optional[date] = None,
    ) -> ComprehensivePreventionPlan:
        """Main synthesis pipeline generating a 30-day comprehensive prevention plan."""
        if not start_date:
            start_date = date.today()
        end_date = start_date + timedelta(days=30)

        # 1. Determine dominant clinical focus & base template
        dominant_domain, target_tier = self._identify_dominant_domain(plan_input)
        base_template = self._select_template(dominant_domain)

        # 2. Match candidate intervention rules
        candidate_rules = self._match_rules(plan_input, dominant_domain)

        # 3. Apply constraints, adaptations, and 5-tier prioritization ranking
        prioritized_actions = self._prioritize_actions(candidate_rules, plan_input)

        # 4. Formulate SMART Goals (merged from template, clinician recs, and user goals)
        goals = self._formulate_smart_goals(base_template, plan_input)

        # 5. Build 30-Day Daily Tasks (Rotating through pillars with day-specific targets)
        daily_tasks = self._build_30_day_tasks(prioritized_actions, plan_input, base_template)

        # 6. Build Scheduled Reminders
        reminders = self._build_reminders(candidate_rules, plan_input)

        # 7. Curate Educational Content
        educational_modules = self._curate_educational_content(candidate_rules, plan_input)

        # 8. Structure Measurement Schedule
        measurements = self._build_measurement_schedule(base_template, candidate_rules, plan_input)

        # 9. Formulate Clinical Follow-Up Schedule
        follow_ups = self._formulate_follow_up_schedule(base_template, plan_input, target_tier)

        # 10. Check if clinician workflow review is required
        clinician_required = self._is_clinician_workflow_required(plan_input, target_tier)

        title = f"SevaHealth 30-Day Prevention Journey: {base_template.name}"
        if plan_input.risk_trajectory == "WORSENING":
            title += " (Intensive Stabilization)"

        return ComprehensivePreventionPlan(
            id=str(uuid.uuid4()),
            tenant_id=plan_input.tenant_id,
            citizen_id=plan_input.citizen_id,
            title=title,
            focus_domain=base_template.name,
            start_date=start_date,
            end_date=end_date,
            goals=goals,
            actions=prioritized_actions,
            daily_tasks=daily_tasks,
            reminders=reminders,
            educational_content=educational_modules,
            measurements=measurements,
            follow_up_schedule=follow_ups,
            adherence_percentage=0.0,
            clinician_workflow_required=clinician_required,
            clinician_review_status="PENDING" if clinician_required else "NOT_REQUIRED",
        )

    def _identify_dominant_domain(self, plan_input: PreventionPlanInput) -> tuple[str, str]:
        """Identifies dominant domain from risk profile or clinician recommendations."""
        rp = plan_input.risk_profile or {}
        domains = rp.get("domains", {})
        overall_tier = rp.get("overall_tier", "MODERATE")

        # Check domain scores
        d_scores = {
            "diabetes": domains.get("diabetes_risk", 0.0) if isinstance(domains, dict) else getattr(domains, "diabetes_risk", 0.0),
            "hypertension": domains.get("hypertension_risk", 0.0) if isinstance(domains, dict) else getattr(domains, "hypertension_risk", 0.0),
            "cardiovascular": domains.get("cardiovascular_risk", 0.0) if isinstance(domains, dict) else getattr(domains, "cardiovascular_risk", 0.0),
            "obesity": domains.get("metabolic_syndrome_risk", 0.0) if isinstance(domains, dict) else getattr(domains, "metabolic_syndrome_risk", 0.0),
            "renal": domains.get("ckd_risk", 0.0) if isinstance(domains, dict) else getattr(domains, "ckd_risk", 0.0),
        }

        # Check lifestyle smoking / alcohol flags
        ls = plan_input.lifestyle
        if ls.get("smoking") or ls.get("tobacco"):
            d_scores["cardiovascular"] += 0.25

        # Pick max domain
        dominant = max(d_scores, key=d_scores.get) if d_scores else "diabetes"
        if d_scores.get(dominant, 0.0) < 0.20:
            dominant = "general_vitality"

        return dominant, str(overall_tier)

    def _select_template(self, domain: str) -> PreventionTemplate:
        mapping = {
            "diabetes": "prediabetes_reversal",
            "hypertension": "hypertension_vascular",
            "cardiovascular": "cardiovascular_protection",
            "obesity": "metabolic_weight_loss",
            "renal": "renal_preservation",
        }
        template_key = mapping.get(domain, "prediabetes_reversal")
        return PREVENTION_TEMPLATES.get(template_key, PREVENTION_TEMPLATES["prediabetes_reversal"])

    def _match_rules(self, plan_input: PreventionPlanInput, dominant_domain: str) -> List[InterventionRule]:
        all_rules = rule_registry.list_rules()
        matched: List[InterventionRule] = []

        rp = plan_input.risk_profile or {}
        tier = str(rp.get("overall_tier", "MODERATE")).upper()
        traj = str(plan_input.risk_trajectory or "STABLE").upper()
        ls = plan_input.lifestyle

        is_smoker = bool(ls.get("smoking") or ls.get("tobacco"))
        is_alcohol = bool(ls.get("alcohol"))
        poor_sleep = bool(ls.get("sleep_hours", 7.0) < 6.5 or ls.get("poor_sleep"))
        sedentary = bool(ls.get("steps", 8000) < 5000 or ls.get("sedentary"))

        for rule in all_rules:
            if not rule.is_active:
                continue

            # Domain trigger match
            domain_match = (
                not rule.risk_domain_triggers or
                dominant_domain in rule.risk_domain_triggers or
                "general" in rule.risk_domain_triggers
            )

            # Lifestyle trigger match
            lifestyle_match = True
            if rule.lifestyle_triggers:
                lifestyle_match = False
                if "SMOKER" in rule.lifestyle_triggers and is_smoker:
                    lifestyle_match = True
                if "ALCOHOL_CONSUMER" in rule.lifestyle_triggers and is_alcohol:
                    lifestyle_match = True
                if "POOR_SLEEP" in rule.lifestyle_triggers and poor_sleep:
                    lifestyle_match = True
                if "SEDENTARY" in rule.lifestyle_triggers and sedentary:
                    lifestyle_match = True

            # Trajectory trigger match (e.g. worsening trajectory triggers clinical follow-up)
            trajectory_match = (
                not rule.trajectory_triggers or
                traj in rule.trajectory_triggers
            )

            if domain_match and (lifestyle_match or trajectory_match):
                matched.append(rule)

        return matched

    def _prioritize_actions(
        self,
        candidate_rules: List[InterventionRule],
        plan_input: PreventionPlanInput,
    ) -> List[PrioritizedAction]:
        """Applies constraint adaptations and sorts candidate actions strictly by:
        1. Safety
        2. Evidence
        3. Expected Benefit
        4. Feasibility
        5. Patient Preference
        """
        actions: List[PrioritizedAction] = []
        constraints = [c.upper() for c in plan_input.constraints]
        preferences = plan_input.preferences
        comm_resources = plan_input.available_community_resources

        for rule in candidate_rules:
            # Check for safety / constraint conflict
            is_contraindicated = any(c in rule.contraindicated_constraints for c in constraints)
            safety_notes = None

            if is_contraindicated and rule.alternative_action_title:
                # Safe substitution applied
                title = rule.alternative_action_title
                desc = rule.alternative_description or rule.action_description
                safety_notes = f"Safety Substitution: Adapted to accommodate {', '.join(constraints)}."
                feasibility_score = 0.95
            elif is_contraindicated:
                # Skip action if unsafe and no alternative exists
                continue
            else:
                title = rule.action_title
                desc = rule.action_description
                feasibility_score = 0.85

            # Boost feasibility if local community resource exists
            if comm_resources:
                if rule.category == InterventionCategory.PHYSICAL_ACTIVITY and any("park" in str(r).lower() or "walking" in str(r).lower() for r in comm_resources):
                    feasibility_score = min(1.0, feasibility_score + 0.10)
                if rule.category == InterventionCategory.STRESS_MANAGEMENT and any("yoga" in str(r).lower() for r in comm_resources):
                    feasibility_score = min(1.0, feasibility_score + 0.10)

            # Preference matching
            preference_score = 0.70
            if rule.category == InterventionCategory.NUTRITION:
                diet_pref = str(preferences.get("dietary_pattern", "")).upper()
                if "VEGETARIAN" in diet_pref or "MILLET" in str(preferences).upper():
                    preference_score = 0.95
            elif rule.category == InterventionCategory.PHYSICAL_ACTIVITY:
                act_pref = str(preferences.get("exercise_type", "")).upper()
                if "WALKING" in act_pref or "YOGA" in act_pref:
                    preference_score = 0.90

            actions.append(PrioritizedAction(
                category=rule.category,
                title=title,
                description=desc,
                frequency=rule.frequency,
                target_metric=rule.target_metric,
                priority_level=rule.priority_level,
                evidence_citation=rule.evidence_citation,
                expected_benefit_score=rule.expected_benefit_score,
                feasibility_score=feasibility_score,
                preference_match_score=preference_score,
                safety_notes=safety_notes,
            ))

        # Sort actions strictly by:
        # 1. priority_level (1=Safety, 2=Evidence, 3=Benefit, 4=Feasibility, 5=Preference)
        # 2. expected_benefit_score descending
        # 3. feasibility_score descending
        # 4. preference_match_score descending
        actions.sort(
            key=lambda a: (
                a.priority_level.value,
                -a.expected_benefit_score,
                -a.feasibility_score,
                -a.preference_match_score,
            )
        )

        return actions

    def _formulate_smart_goals(
        self,
        template: PreventionTemplate,
        plan_input: PreventionPlanInput,
    ) -> List[SMARTGoal]:
        goals = list(template.goals)

        # Merge user goals
        for g_str in plan_input.goals:
            goals.append(SMARTGoal(
                pillar=InterventionCategory.PHYSICAL_ACTIVITY if "step" in g_str.lower() or "walk" in g_str.lower() else InterventionCategory.NUTRITION,
                title=f"Citizen Goal: {g_str}",
                target_metric=g_str,
                timeline_days=30,
                clinical_rationale="Patient-driven goals significantly enhance psychological buy-in and habit formation.",
            ))

        # Merge clinician recommendations
        for cr_str in plan_input.clinician_recommendations:
            goals.append(SMARTGoal(
                pillar=InterventionCategory.CLINICAL_FOLLOWUP,
                title=f"Clinical Recommendation: {cr_str}",
                target_metric=cr_str,
                timeline_days=30,
                clinical_rationale="Doctor prescribed guideline intervention target.",
            ))

        return goals[:5]  # Keep focused on top 5 SMART goals

    def _build_30_day_tasks(
        self,
        prioritized_actions: List[PrioritizedAction],
        plan_input: PreventionPlanInput,
        template: PreventionTemplate,
    ) -> List[DailyTask]:
        """Constructs an actionable 30-day daily task schedule rotating through
        lifestyle pillars and incorporating citizen constraints and preferences.
        """
        tasks: List[DailyTask] = []
        action_pool = prioritized_actions if prioritized_actions else []

        # Fallback pillar rotations
        for day in range(1, 31):
            if action_pool:
                action = action_pool[(day - 1) % len(action_pool)]
                # Map InterventionCategory to InterventionPillar
                p_map = {
                    InterventionCategory.NUTRITION: InterventionPillar.NUTRITION,
                    InterventionCategory.PHYSICAL_ACTIVITY: InterventionPillar.PHYSICAL_ACTIVITY,
                    InterventionCategory.SLEEP: InterventionPillar.SLEEP_HYGIENE,
                    InterventionCategory.STRESS_MANAGEMENT: InterventionPillar.STRESS_AND_LIFESTYLE,
                }
                pillar = p_map.get(action.category, InterventionPillar.NUTRITION)
                title = f"Day {day}: {action.title}"
                desc = action.description
                metric = action.target_metric or "Complete daily protocol"
            else:
                pillar = InterventionPillar.NUTRITION
                title = f"Day {day}: Healthy Plate Habit"
                desc = "Incorporate raw vegetables and seasonal whole grain."
                metric = "1 serving"

            tasks.append(DailyTask(
                id=str(uuid.uuid4()),
                day=day,
                pillar=pillar,
                title=title,
                description=desc,
                target_metric=metric,
                completed=False,
            ))

        return tasks

    def _build_reminders(
        self,
        candidate_rules: List[InterventionRule],
        plan_input: PreventionPlanInput,
    ) -> List[ScheduledReminder]:
        reminders: List[ScheduledReminder] = []
        pref_channel = plan_input.preferences.get("reminder_channel", "PUSH_NOTIFICATION")
        pref_time = plan_input.preferences.get("preferred_reminder_time")

        for rule in candidate_rules:
            if rule.reminder_title and rule.reminder_message:
                t = pref_time or rule.reminder_time
                reminders.append(ScheduledReminder(
                    category=rule.category,
                    title=rule.reminder_title,
                    scheduled_time=t,
                    frequency="DAILY" if "daily" in rule.frequency.lower() else "WEEKLY",
                    channel=pref_channel,
                    message_content=rule.reminder_message,
                ))

        return reminders[:6]

    def _curate_educational_content(
        self,
        candidate_rules: List[InterventionRule],
        plan_input: PreventionPlanInput,
    ) -> List[EducationalModule]:
        modules: List[EducationalModule] = []
        for rule in candidate_rules:
            if rule.educational_module_title and rule.educational_takeaway:
                modules.append(EducationalModule(
                    category=rule.category,
                    title=rule.educational_module_title,
                    key_takeaway=rule.educational_takeaway,
                    reading_time_mins=3,
                    cultural_adaptation=rule.cultural_adaptation or "Adapted for regional dietary and physical activity patterns.",
                    evidence_summary=rule.evidence_citation,
                ))
        return modules[:5]

    def _build_measurement_schedule(
        self,
        template: PreventionTemplate,
        candidate_rules: List[InterventionRule],
        plan_input: PreventionPlanInput,
    ) -> List[MeasurementSchedule]:
        measurements: List[MeasurementSchedule] = list(template.standard_measurements)
        for rule in candidate_rules:
            if rule.measurement_biometric:
                if not any(m.biometric == rule.measurement_biometric for m in measurements):
                    measurements.append(MeasurementSchedule(
                        biometric=rule.measurement_biometric,
                        frequency=rule.measurement_frequency or "Weekly",
                        target_range=rule.measurement_target or "Optimal reference range",
                        instructions=rule.measurement_instructions or "Perform seated resting measurement.",
                    ))
        return measurements

    def _formulate_follow_up_schedule(
        self,
        template: PreventionTemplate,
        plan_input: PreventionPlanInput,
        target_tier: str,
    ) -> List[FollowUpEvent]:
        follow_ups: List[FollowUpEvent] = list(template.standard_followups)

        # If trajectory is worsening or tier is critical, add an early urgent check-in
        if plan_input.risk_trajectory == "WORSENING" or target_tier in ["HIGH", "CRITICAL"]:
            if not any(f.day_number == 3 for f in follow_ups):
                follow_ups.insert(0, FollowUpEvent(
                    day_number=3,
                    provider_role="ASHA_WORKER",
                    channel="HOME_VISIT",
                    agenda="Early compliance check, verify understanding of prevention plan, verify absence of acute red-flag symptoms.",
                ))

        return follow_ups

    def _is_clinician_workflow_required(self, plan_input: PreventionPlanInput, target_tier: str) -> bool:
        """Determines if the care plan requires physician review.
        Triggers when:
        - Risk tier is HIGH or CRITICAL
        - Risk trajectory is WORSENING
        - Clinician recommendations are specified
        """
        if target_tier in ["HIGH", "CRITICAL"]:
            return True
        if plan_input.risk_trajectory == "WORSENING":
            return True
        if plan_input.clinician_recommendations:
            return True
        return False


# Global singleton instance
prevention_intervention_engine = PreventionInterventionEngine()
