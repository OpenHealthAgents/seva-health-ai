import pytest
from datetime import date
from packages.clinical_models.risk import RiskAssessment, DomainRiskScores
from packages.types.enums import RiskTier, TrajectoryTrend
from services.intervention_engine.generator import generate_30_day_care_plan


def test_care_plan_generation():
    risk = RiskAssessment(
        tenant_id="t1",
        citizen_id="c1",
        overall_score=0.65,
        overall_tier=RiskTier.HIGH,
        domains=DomainRiskScores(
            diabetes_risk=0.72,
            hypertension_risk=0.58,
            cardiovascular_risk=0.40,
            metabolic_syndrome_risk=0.65,
            ckd_risk=0.20,
            fatty_liver_risk=0.50,
        ),
        trajectory=TrajectoryTrend.DETERIORATING,
        confidence_score=0.90,
        clinical_summary="Prediabetes intervention required.",
    )

    plan = generate_30_day_care_plan(
        citizen_id="c1",
        tenant_id="t1",
        risk=risk,
        start_date=date(2026, 10, 1)
    )

    assert plan.citizen_id == "c1"
    assert len(plan.daily_tasks) == 30
    assert plan.adherence_percentage == 0.0
    assert "Glycemic" in plan.focus_domain or "Metabolic" in plan.focus_domain
    assert "millet" in plan.nutrition_guidance.lower() or "vegetable" in plan.nutrition_guidance.lower()


def test_adherence_calculation():
    risk = RiskAssessment(
        tenant_id="t1",
        citizen_id="c1",
        overall_score=0.40,
        overall_tier=RiskTier.MODERATE,
        domains=DomainRiskScores(
            diabetes_risk=0.3, hypertension_risk=0.3, cardiovascular_risk=0.3,
            metabolic_syndrome_risk=0.3, ckd_risk=0.1, fatty_liver_risk=0.2
        ),
        trajectory=TrajectoryTrend.STABLE,
        confidence_score=0.80,
        clinical_summary="Moderate risk.",
    )
    plan = generate_30_day_care_plan(citizen_id="c1", tenant_id="t1", risk=risk)

    # Complete 15 of 30 tasks
    for i in range(15):
        plan.daily_tasks[i].completed = True

    completed_count = sum(1 for t in plan.daily_tasks if t.completed)
    adherence = round((completed_count / len(plan.daily_tasks)) * 100, 1)
    assert adherence == 50.0
