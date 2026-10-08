import pytest
from packages.clinical_models.observations import Observation
from packages.types.enums import RiskTier, TrajectoryTrend
from services.risk_engine.evaluator import evaluate_ncd_domains


def test_evaluate_ncd_domains_prediabetic():
    observations = [
        Observation(citizen_id="c1", tenant_id="t1", code="HBA1C", value=6.2, unit="%", loinc_code="4548-4", display_name="HbA1c"),
        Observation(citizen_id="c1", tenant_id="t1", code="SYSTOLIC_BP", value=138.0, unit="mmHg", loinc_code="8480-6", display_name="Systolic BP"),
        Observation(citizen_id="c1", tenant_id="t1", code="DIASTOLIC_BP", value=88.0, unit="mmHg", loinc_code="8462-4", display_name="Diastolic BP"),
        Observation(citizen_id="c1", tenant_id="t1", code="WAIST_CIRCUMFERENCE", value=96.0, unit="cm", loinc_code="8280-0", display_name="Waist"),
    ]

    domains, score, tier, trajectory, drivers, protective = evaluate_ncd_domains(
        observations=observations,
        idrs_score=60,
        gender="MALE",
        smoker=False,
    )

    assert domains.diabetes_risk >= 0.60
    assert domains.hypertension_risk >= 0.50
    assert tier in [RiskTier.HIGH, RiskTier.CRITICAL]
    assert trajectory == TrajectoryTrend.DETERIORATING
    assert len(drivers) >= 2
    # Check that explainability drivers include HbA1c
    assert any("Glycemia" in d.feature_name or "Diabetic" in d.feature_name for d in drivers)
    # Check that non-smoker is listed as protective factor
    assert any("Tobacco Abstinence" in p.feature_name for p in protective)


def test_evaluate_ncd_domains_healthy_baseline():
    observations = [
        Observation(citizen_id="c2", tenant_id="t1", code="HBA1C", value=5.1, unit="%", loinc_code="4548-4", display_name="HbA1c"),
        Observation(citizen_id="c2", tenant_id="t1", code="SYSTOLIC_BP", value=116.0, unit="mmHg", loinc_code="8480-6", display_name="Systolic BP"),
        Observation(citizen_id="c2", tenant_id="t1", code="DIASTOLIC_BP", value=74.0, unit="mmHg", loinc_code="8462-4", display_name="Diastolic BP"),
        Observation(citizen_id="c2", tenant_id="t1", code="BMI", value=21.2, unit="kg/m2", loinc_code="39156-5", display_name="BMI"),
    ]

    domains, score, tier, trajectory, drivers, protective = evaluate_ncd_domains(
        observations=observations,
        idrs_score=10,
        gender="FEMALE",
        smoker=False,
    )

    assert tier == RiskTier.LOW
    assert trajectory == TrajectoryTrend.IMPROVING
    assert domains.diabetes_risk < 0.25
    assert domains.hypertension_risk < 0.25
