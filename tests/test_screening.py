import pytest
from packages.clinical_models.screening import IDRSSurvey, CBACSurvey
from services.screening.calculator import calculate_idrs, calculate_cbac


def test_idrs_calculation_high_risk():
    # Person >= 50 (30 pts), waist >= 100 (20 pts), sedentary (20 pts), both parents (20 pts) -> 90 pts (High Risk)
    survey = IDRSSurvey(
        age_category=">=50",
        waist_category=">=100",
        physical_activity="Sedentary",
        family_history="Both parents",
    )
    score = calculate_idrs(survey)
    assert score == 90
    assert score >= 60  # ICMR High Risk threshold


def test_idrs_calculation_low_risk():
    survey = IDRSSurvey(
        age_category="<35",
        waist_category="<90",
        physical_activity="Vigorous",
        family_history="None",
    )
    score = calculate_idrs(survey)
    assert score == 0
    assert score < 30  # ICMR Low Risk threshold


def test_cbac_calculation():
    cbac = CBACSurvey(
        age_over_30=True,               # 2 pts
        tobacco_user=True,              # 2 pts
        alcohol_consumption=False,
        waist_circumference_exceeded=True, # 2 pts
        physical_activity_below_150min=True, # 2 pts
        family_history_diabetes_or_htn=False,
    )
    score = calculate_cbac(cbac)
    assert score == 8
    assert score >= 4  # Referral recommended threshold
