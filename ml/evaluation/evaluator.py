"""Evaluation interface orchestrating discrimination, calibration, fairness, and missingness tests.

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ml.evaluation.demographics import DemographicEvaluationReport, DemographicEvaluator
from ml.evaluation.metrics import (
    ClinicalEvaluationMetrics,
    ClinicalMetricsCalculator,
    ConfusionMatrixValues,
)
from ml.evaluation.missingness import (
    MissingDataSensitivityAnalyzer,
    MissingDataSensitivityReport,
)
from ml.features.feature_engineering import ClinicalFeatureEngineer
from ml.models.base import BaseRiskModel
from ml.preprocessing.pipeline import ClinicalDataPreprocessor


@dataclass
class CompleteEvaluationReport:
    model_name: str
    model_version: str
    evaluation_version: str
    training_data_version: str
    feature_version: str
    timestamp: str
    overall_metrics: ClinicalEvaluationMetrics
    optimal_threshold: float
    demographic_evaluation: DemographicEvaluationReport
    missing_data_sensitivity: MissingDataSensitivityReport
    clinical_disclaimer: str = (
        "RESEARCH DEMONSTRATION ONLY: This evaluation report reflects simulated performance "
        "on synthetic cohorts. The model and metrics are NOT clinically validated and must not "
        "be used for unsupervised clinical decision-making or diagnostic claims."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_json(self, filepath: Union[str, Path]) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def generate_markdown_summary(self) -> str:
        om = self.overall_metrics
        cm = om.confusion_matrix
        cal = om.calibration
        demo = self.demographic_evaluation
        miss = self.missing_data_sensitivity

        lines = [
            f"# Clinical Model Evaluation Report: {self.model_name} ({self.model_version})",
            "",
            "> ⚠️ **IMPORTANT DISCLAIMER**: For research and demonstration purposes only. "
            "This model and evaluation do **NOT** claim clinical validation. Not cleared for medical diagnostic use.",
            "",
            "## 1. Version Lineage & Provenance",
            f"- **Model Version**: `{self.model_version}`",
            f"- **Training Data Version**: `{self.training_data_version}`",
            f"- **Feature Version**: `{self.feature_version}`",
            f"- **Evaluation Version**: `{self.evaluation_version}`",
            f"- **Evaluation Timestamp**: `{self.timestamp}`",
            f"- **Evaluated Samples**: {om.num_samples:,} (Prevalence: {om.prevalence*100:.1f}%)",
            "",
            "## 2. Core Clinical Performance Metrics",
            "| Metric | Value | Interpretation / Goal |",
            "|---|---|---|",
            f"| **AUROC** | **{om.auroc:.4f}** | Discrimination (Area under ROC) |",
            f"| **AUPRC** | **{om.auprc:.4f}** | Precision-Recall curve area |",
            f"| **Sensitivity (Recall)** | **{om.sensitivity*100:.2f}%** | True Positive Rate at threshold {om.decision_threshold:.2f} |",
            f"| **Specificity** | **{om.specificity*100:.2f}%** | True Negative Rate at threshold {om.decision_threshold:.2f} |",
            f"| **PPV (Precision)** | **{om.ppv*100:.2f}%** | Positive Predictive Value |",
            f"| **NPV** | **{om.npv*100:.2f}%** | Negative Predictive Value |",
            f"| **Brier Score** | **{cal.brier_score:.4f}** | Overall calibration error (lower is better) |",
            f"| **Expected Calib. Error (ECE)** | **{cal.expected_calibration_error:.4f}** | Probability reliability gap |",
            f"| **Max Calib. Error (MCE)** | **{cal.max_calibration_error:.4f}** | Maximum reliability gap |",
            f"| **Calibration Slope** | **{cal.calibration_slope:.3f}** | Target ~1.0 |",
            f"| **Calibration Intercept** | **{cal.calibration_intercept:.3f}** | Target ~0.0 |",
            f"| **Optimal Threshold (Youden's J)** | **{self.optimal_threshold:.3f}** | Optimized for balanced sensitivity/specificity |",
            "",
            "### Confusion Matrix (Threshold = {:.2f})".format(om.decision_threshold),
            "| | Actual Positive | Actual Negative |",
            "|---|---|---|",
            f"| **Predicted Positive** | TP: **{cm.true_positives:,}** | FP: **{cm.false_positives:,}** |",
            f"| **Predicted Negative** | FN: **{cm.false_negatives:,}** | TN: **{cm.true_negatives:,}** |",
            "",
            "## 3. Subgroup Performance & Demographic Equity",
            "### Performance by Sex",
            "| Sex | N | Prevalence | AUROC | Sensitivity | Specificity | PPV | NPV | Brier |",
            "|---|---|---|---|---|---|---|---|---|",
        ]

        for s in demo.performance_by_sex:
            lines.append(
                f"| {s.group_name} | {s.sample_size} | {s.prevalence*100:.1f}% | {s.auroc:.4f} | "
                f"{s.sensitivity*100:.1f}% | {s.specificity*100:.1f}% | {s.ppv*100:.1f}% | {s.npv*100:.1f}% | {s.brier_score:.4f} |"
            )

        lines.extend([
            "",
            "### Performance by Age Bracket",
            "| Age Bracket | N | Prevalence | AUROC | Sensitivity | Specificity | PPV | NPV | Brier |",
            "|---|---|---|---|---|---|---|---|---|",
        ])
        for a in demo.performance_by_age:
            lines.append(
                f"| {a.group_name} | {a.sample_size} | {a.prevalence*100:.1f}% | {a.auroc:.4f} | "
                f"{a.sensitivity*100:.1f}% | {a.specificity*100:.1f}% | {a.ppv*100:.1f}% | {a.npv*100:.1f}% | {a.brier_score:.4f} |"
            )

        lines.extend([
            "",
            "### Performance by Demographic / Regional Cohort",
            "| Demographic Group | N | Prevalence | AUROC | Sensitivity | Specificity | PPV | NPV |",
            "|---|---|---|---|---|---|---|---|",
        ])
        for g in demo.performance_by_demographic_groups:
            lines.append(
                f"| {g.group_name} | {g.sample_size} | {g.prevalence*100:.1f}% | {g.auroc:.4f} | "
                f"{g.sensitivity*100:.1f}% | {g.specificity*100:.1f}% | {g.ppv*100:.1f}% | {g.npv*100:.1f}% |"
            )

        lines.extend([
            "",
            "### Fairness & Disparity Summary",
        ])
        for k, v in demo.disparity_summary.items():
            lines.append(f"- **{k.replace('_', ' ').title()}**: `{v}`")

        lines.extend([
            "",
            "## 4. Missing-Data Sensitivity & Degradation Curve",
            f"> {miss.resilience_summary}",
            "",
            "### Performance Under Increasing Feature Missingness Rates",
            "| Condition | Simulated Missing Rate | AUROC | Δ AUROC | Brier Score | Sensitivity | Specificity |",
            "|---|---|---|---|---|---|---|",
            f"| Baseline (Observed) | 0.0% | {miss.baseline_auroc:.4f} | 0.0000 | {miss.baseline_brier:.4f} | {om.sensitivity*100:.1f}% | {om.specificity*100:.1f}% |",
        ])
        for r in miss.rate_sensitivity_curve:
            lines.append(
                f"| {r.condition_name} | {r.missing_rate_simulated*100:.0f}% | {r.auroc:.4f} | "
                f"{r.delta_auroc_from_baseline:+.4f} | {r.brier_score:.4f} | {r.sensitivity*100:.1f}% | {r.specificity*100:.1f}% |"
            )

        lines.extend([
            "",
            "### Clinical Panel Dropouts (Point-of-Care Resource Constraints)",
            "| Panel Dropout Scenario | AUROC | Δ AUROC | Brier Score | Sensitivity | Specificity |",
            "|---|---|---|---|---|---|",
        ])
        for p in miss.panel_dropout_evaluations:
            lines.append(
                f"| {p.condition_name} | {p.auroc:.4f} | {p.delta_auroc_from_baseline:+.4f} | "
                f"{p.brier_score:.4f} | {p.sensitivity*100:.1f}% | {p.specificity*100:.1f}% |"
            )

        lines.extend([
            "",
            "## 5. Non-Clinical Validation Affirmation",
            f"{self.clinical_disclaimer}",
        ])

        return "\n".join(lines)


class ModelEvaluator:
    """Evaluation interface for clinical AI models."""

    def __init__(self, evaluation_version: str = "v1.0.0"):
        self.evaluation_version = evaluation_version

    def evaluate(
        self,
        model: BaseRiskModel,
        preprocessor: ClinicalDataPreprocessor,
        feature_engineer: ClinicalFeatureEngineer,
        test_df: pd.DataFrame,
        target_col: str = "event_outcome",
        decision_threshold: float = 0.5,
        training_data_version: str = "v1.0.0",
        feature_version: str = "v1.0.0",
    ) -> CompleteEvaluationReport:
        """Runs the entire evaluation suite."""
        y_true = test_df[target_col].values

        # Feature transform and preprocessing
        fe_df = feature_engineer.transform(test_df)
        drop_cols = ["patient_id", target_col]
        clean_df = fe_df.drop(columns=[c for c in drop_cols if c in fe_df.columns], errors="ignore")
        X_proc = preprocessor.transform(clean_df)

        y_prob = model.predict_proba(X_proc)[:, 1]

        # 1. Overall Metrics
        overall_metrics = ClinicalMetricsCalculator.compute_all_metrics(
            y_true=y_true,
            y_prob=y_prob,
            threshold=decision_threshold,
        )

        # 2. Optimal Threshold Search
        optimal_thresh = ClinicalMetricsCalculator.find_optimal_threshold(
            y_true=y_true,
            y_prob=y_prob,
            metric="youden",
        )

        # 3. Demographic & Subgroup Evaluation
        demographic_report = DemographicEvaluator.evaluate_subgroups(
            df_raw=test_df,
            y_prob=y_prob,
            target_col=target_col,
            threshold=decision_threshold,
        )

        # 4. Missing-Data Sensitivity Analysis
        missing_analyzer = MissingDataSensitivityAnalyzer(
            model=model,
            preprocessor=preprocessor,
            feature_engineer=feature_engineer,
        )
        missing_report = missing_analyzer.evaluate(
            test_df_raw=test_df,
            target_col=target_col,
            threshold=decision_threshold,
        )

        import datetime
        timestamp_str = datetime.datetime.now().isoformat()

        return CompleteEvaluationReport(
            model_name=model.model_name,
            model_version=model.model_version,
            evaluation_version=self.evaluation_version,
            training_data_version=training_data_version,
            feature_version=feature_version,
            timestamp=timestamp_str,
            overall_metrics=overall_metrics,
            optimal_threshold=optimal_thresh,
            demographic_evaluation=demographic_report,
            missing_data_sensitivity=missing_report,
        )
