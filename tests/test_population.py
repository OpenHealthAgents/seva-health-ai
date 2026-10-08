import pytest
from services.population_intelligence.analytics import (
    get_regional_epidemiological_metrics,
    calculate_intervention_outcome_delta,
)


def test_regional_metrics():
    metrics = get_regional_epidemiological_metrics()
    assert metrics["state"] == "Karnataka"
    assert "prevalence_rates" in metrics
    assert len(metrics["districts"]) == 5
    assert any(d["district_name"] == "Mysuru" for d in metrics["districts"])


def test_intervention_outcome_delta():
    delta = calculate_intervention_outcome_delta()
    assert delta["analysis_cohort_size"] == 2400
    high_group = delta["cohorts"]["high_adherence_group"]
    low_group = delta["cohorts"]["low_adherence_group"]

    # Clinically meaningful systolic BP reduction in high adherence group
    assert high_group["mean_systolic_bp_change_mmhg"] < 0
    # Low adherence group should not show significant reduction
    assert low_group["mean_systolic_bp_change_mmhg"] >= 0
