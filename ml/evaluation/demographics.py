"""Demographic subgroup and fairness evaluation.

Measures clinical model performance sliced by:
- Age groups (<40, 40-54, 55-69, 70+)
- Sex (Female, Male)
- Demographic Groups (e.g., Regional / Rural-Urban cohorts)

Calculates disparity metrics (Equal Opportunity Difference, Demographic Parity Difference).
DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ml.evaluation.metrics import ClinicalEvaluationMetrics, ClinicalMetricsCalculator


@dataclass
class SubgroupPerformance:
    group_name: str
    attribute_name: str
    sample_size: int
    positive_count: int
    prevalence: float
    auroc: float
    auprc: float
    sensitivity: float
    specificity: float
    ppv: float
    npv: float
    brier_score: float
    ece: float


@dataclass
class DemographicEvaluationReport:
    performance_by_age: List[SubgroupPerformance]
    performance_by_sex: List[SubgroupPerformance]
    performance_by_demographic_groups: List[SubgroupPerformance]
    disparity_summary: Dict[str, float]
    disclaimer: str = (
        "RESEARCH DEMONSTRATION ONLY: Subgroup fairness evaluation on synthetic cohort. "
        "Does not constitute clinical validation or regulatory clearance. NOT clinically validated."
    )


class DemographicEvaluator:
    """Evaluates clinical risk models across demographic stratifications."""

    AGE_BINS = [0, 40, 55, 70, 150]
    AGE_LABELS = ["<40", "40-54", "55-69", "70+"]

    @classmethod
    def evaluate_subgroups(
        cls,
        df_raw: pd.DataFrame,
        y_prob: np.ndarray,
        target_col: str = "event_outcome",
        threshold: float = 0.5,
    ) -> DemographicEvaluationReport:
        """Computes performance across Age, Sex, and Demographic Groups."""
        y_true = df_raw[target_col].values
        y_pred = (y_prob >= threshold).astype(int)

        # 1. Performance by Age
        age_series = df_raw["age"]
        age_groups = pd.cut(age_series, bins=cls.AGE_BINS, labels=cls.AGE_LABELS, right=False)
        age_results = cls._evaluate_attribute(
            subgroup_series=age_groups,
            attr_name="age_bracket",
            y_true=y_true,
            y_prob=y_prob,
            threshold=threshold,
        )

        # 2. Performance by Sex
        sex_results = cls._evaluate_attribute(
            subgroup_series=df_raw["sex"],
            attr_name="sex",
            y_true=y_true,
            y_prob=y_prob,
            threshold=threshold,
        )

        # 3. Performance by Demographic Group
        demo_col = "demographic_group" if "demographic_group" in df_raw.columns else "region"
        demo_results = cls._evaluate_attribute(
            subgroup_series=df_raw[demo_col],
            attr_name="demographic_group",
            y_true=y_true,
            y_prob=y_prob,
            threshold=threshold,
        )

        # 4. Disparity Summary
        disparity = cls._calculate_disparities(
            sex_results=sex_results,
            age_results=age_results,
            demo_results=demo_results,
            df_raw=df_raw,
            y_pred=y_pred,
        )

        return DemographicEvaluationReport(
            performance_by_age=age_results,
            performance_by_sex=sex_results,
            performance_by_demographic_groups=demo_results,
            disparity_summary=disparity,
        )

    @staticmethod
    def _evaluate_attribute(
        subgroup_series: pd.Series,
        attr_name: str,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        threshold: float,
    ) -> List[SubgroupPerformance]:
        results: List[SubgroupPerformance] = []
        unique_groups = subgroup_series.dropna().unique()

        for group in sorted(unique_groups):
            mask = (subgroup_series == group).values
            n_sub = int(np.sum(mask))
            if n_sub < 10:
                continue

            sub_y_true = y_true[mask]
            sub_y_prob = y_prob[mask]

            pos_count = int(np.sum(sub_y_true))
            metrics = ClinicalMetricsCalculator.compute_all_metrics(
                sub_y_true, sub_y_prob, threshold=threshold
            )

            results.append(
                SubgroupPerformance(
                    group_name=str(group),
                    attribute_name=attr_name,
                    sample_size=n_sub,
                    positive_count=pos_count,
                    prevalence=round(float(pos_count / n_sub), 4),
                    auroc=metrics.auroc,
                    auprc=metrics.auprc,
                    sensitivity=metrics.sensitivity,
                    specificity=metrics.specificity,
                    ppv=metrics.ppv,
                    npv=metrics.npv,
                    brier_score=metrics.calibration.brier_score,
                    ece=metrics.calibration.expected_calibration_error,
                )
            )

        return results

    @staticmethod
    def _calculate_disparities(
        sex_results: List[SubgroupPerformance],
        age_results: List[SubgroupPerformance],
        demo_results: List[SubgroupPerformance],
        df_raw: pd.DataFrame,
        y_pred: np.ndarray,
    ) -> Dict[str, float]:
        """Calculates fairness disparity metrics."""
        summary = {}

        # Sex Disparity
        if len(sex_results) >= 2:
            aurocs = [r.auroc for r in sex_results if not np.isnan(r.auroc)]
            sensitivities = [r.sensitivity for r in sex_results]
            if aurocs:
                summary["sex_max_auroc_difference"] = round(max(aurocs) - min(aurocs), 4)
            if sensitivities:
                # Equal opportunity difference (diff in sensitivity/TPR)
                summary["sex_equal_opportunity_diff"] = round(max(sensitivities) - min(sensitivities), 4)

            # Demographic parity difference
            fem_pred_rate = np.mean(y_pred[df_raw["sex"] == "Female"])
            male_pred_rate = np.mean(y_pred[df_raw["sex"] == "Male"])
            summary["sex_demographic_parity_diff"] = round(abs(float(fem_pred_rate - male_pred_rate)), 4)

        # Age Disparity
        if age_results:
            age_aurocs = [r.auroc for r in age_results if not np.isnan(r.auroc)]
            if age_aurocs:
                summary["age_max_auroc_difference"] = round(max(age_aurocs) - min(age_aurocs), 4)

        # Demographic Group Disparity
        if demo_results:
            demo_aurocs = [r.auroc for r in demo_results if not np.isnan(r.auroc)]
            if demo_aurocs:
                summary["demographic_group_max_auroc_difference"] = round(max(demo_aurocs) - min(demo_aurocs), 4)

        return summary
