from packages.clinical_models.screening import IDRSSurvey, CBACSurvey


def calculate_idrs(survey: IDRSSurvey) -> int:
    """Calculates Indian Diabetes Risk Score (0 - 100 points).
    < 30: Low Risk | 30 - 50: Medium Risk | >= 60: High Risk
    """
    score = 0

    # Age criteria
    if survey.age_category == ">=50":
        score += 30
    elif survey.age_category == "35-49":
        score += 20
    else:
        score += 0

    # Waist category
    if ">=100" in survey.waist_category or ">=90" in survey.waist_category:
        score += 20
    elif "90-99" in survey.waist_category or "80-89" in survey.waist_category:
        score += 10
    else:
        score += 0

    # Physical activity
    if survey.physical_activity == "None":
        score += 30
    elif survey.physical_activity == "Sedentary":
        score += 20
    elif survey.physical_activity == "Moderate":
        score += 10
    else:
        score += 0

    # Family history
    if survey.family_history == "Both parents":
        score += 20
    elif survey.family_history == "One parent":
        score += 10
    else:
        score += 0

    return score


def calculate_cbac(survey: CBACSurvey) -> int:
    """Calculates CBAC Score (0 - 10 points). Score >= 4 recommends PHC referral."""
    score = 0
    if survey.age_over_30:
        score += 2
    if survey.tobacco_user:
        score += 2
    if survey.alcohol_consumption:
        score += 1
    if survey.waist_circumference_exceeded:
        score += 2
    if survey.physical_activity_below_150min:
        score += 2
    if survey.family_history_diabetes_or_htn:
        score += 1
    return score
