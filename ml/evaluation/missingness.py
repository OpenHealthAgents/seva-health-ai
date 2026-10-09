"""Missing-data sensitivity evaluation for clinical risk models.

Analyzes model robustness under varying rates of missingness and clinical feature panel dropouts
(e.g., scenarios where laboratory biomarkers or blood pressure measurements are unavailable).

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ml.evaluation.metrics import ClinicalMetricsCalculator
from ml.features.feature_engineering import ClinicalFeatureEngineer
from ml.models.base import BaseRiskModel
from ml.preprocessing.pipeline import ClinicalDataPreprocessor


@dataclass
class MissingnessConditionResult:
    condition_name: str
    missing_rate_simulated: float
    features_affected: List[str]
    auroc: float
    auprc: float
    brier_score: float
    sensitivity: float
    specificity: float
    delta_auroc_from_baseline: float
    delta_brier_from_baseline: float


@dataclass
class MissingDataSensitivityReport:
    baseline_auroc: float
    baseline_brier: float
    rate_sensitivity_curve: List[MissingnessConditionResult]
    panel_dropout_evaluations: List[MissingnessConditionResult]
    resilience_summary: str
    disclaimer: str = (
        "RESEARCH DEMONSTRATION ONLY: Missing-data stress test on demonstration cohort. "
        "Does not constitute clinical validation. NOT clinically validated."
    )


class MissingDataSensitivityAnalyzer:
    """Evaluates how clinical model performance degrades under data missingness."""

    def __init__(
        self,
        model: BaseRiskModel,
        preprocessor: ClinicalDataPreprocessor,
        feature_engineer: ClinicalFeatureEngineer,
        random_state: int = 42,
    ):
        self.model = model
        self.preprocessor = preprocessor
        self.feature_engineer = feature_engineer
        self.random_state = random_state

    def evaluate(
        self,
        test_df_raw: pd.DataFrame,
        target_col: str = "event_outcome",
        threshold: float = 0.5,
    ) -> MissingDataSensitivityReport:
        """Runs systematic missingness stress tests."""
        rng = np.random.RandomState(self.random_state)
        y_true = test_df_raw[target_col].values

        # 1. Baseline Performance
        baseline_prob = self._predict_from_raw(test_df_raw)
        base_metrics = ClinicalMetricsCalculator.compute_all_metrics(
            y_true, baseline_prob, threshold=threshold
        )
        base_auroc = base_metrics.auroc
        base_brier = base_metrics.calibration.brier_score

        # 2. Rate Sensitivity Curve (synthetic MCAR missingness across numerical features)
        candidate_num_cols = [
            c for c in self.preprocessor.numerical_cols_
            if c in test_df_raw.columns and c not in ["age", "event_outcome"]
        ]
        
        rates = [0.10, 0.25, 0.40, 0.60, 0.75]
        rate_results: List[MissingnessConditionResult] = []

        for rate in rates:
            corrupted_df = test_df_raw.copy()
            for col in candidate_num_cols:
                mask = rng.rand(len(corrupted_df)) < rate
                corrupted_df.loc[mask, col] = np.nan

            prob = self._predict_from_raw(corrupted_df)
            m = ClinicalMetricsCalculator.compute_all_metrics(y_true, prob, threshold=threshold)
            rate_results.append(
                MissingnessConditionResult(
                    condition_name=f"Random Missing {int(rate*100)}%",
                    missing_rate_simulated=rate,
                    features_affected=candidate_num_cols,
                    auroc=m.auroc,
                    auprc=m.auprc,
                    brier_score=m.calibration.brier_score,
                    sensitivity=m.sensitivity,
                    specificity=m.specificity,
                    delta_auroc_from_baseline=round(m.auroc - base_auroc, 4),
                    delta_brier_from_baseline=round(m.calibration.brier_score - base_brier, 4),
                )
            )

        # 3. Clinical Panel Dropout Evaluations
        panel_results: List[MissingnessConditionResult] = []

        # Panel A: No Laboratory Tests (Common in primary/rural screening without labs)
        lab_features = [
            "fasting_glucose",
            "hba1c",
            "total_cholesterol",
            "hdl_cholesterol",
            "ldl_cholesterol",
            "triglycerides",
            "serum_creatinine",
        ]
        df_no_labs = test_df_raw.copy()
        for c in lab_features:
            if c in df_no_labs.columns:
                df_no_labs[c] = np.nan

        prob_no_labs = self._predict_from_raw(df_no_labs)
        m_no_labs = ClinicalMetricsCalculator.compute_all_metrics(y_true, prob_no_labs, threshold=threshold)
        panel_results.append(
            MissingnessConditionResult(
                condition_name="No Laboratory Tests (Point-of-Care Unavailable)",
                missing_rate_simulated=1.0,
                features_affected=[c for c in lab_features if c in test_df_raw.columns],
                auroc=m_no_labs.auroc,
                auprc=m_no_labs.auprc,
                brier_score=m_no_labs.calibration.brier_score,
                sensitivity=m_no_labs.sensitivity,
                specificity=m_no_labs.specificity,
                delta_auroc_from_baseline=round(m_no_labs.auroc - base_auroc, 4),
                delta_brier_from_baseline=round(m_no_labs.calibration.brier_score - base_brier, 4),
            )
        )

        # Panel B: No Blood Pressure Measurements
        bp_features = ["systolic_bp", "diastolic_bp"]
        df_no_bp = test_df_raw.copy()
        for c in bp_features:
            if c in df_no_bp.columns:
                df_no_bp[c] = np.nan

        prob_no_bp = self._predict_from_raw(df_no_bp)
        m_no_bp = ClinicalMetricsCalculator.compute_all_metrics(y_true, prob_no_bp, threshold=threshold)
        panel_results.append(
            MissingnessConditionResult(
                condition_name="No Blood Pressure Cuff",
                missing_rate_simulated=1.0,
                features_affected=bp_features,
                auroc=m_no_bp.auroc,
                auprc=m_no_bp.auprc,
                brier_score=m_no_bp.calibration.brier_score,
                sensitivity=m_no_bp.sensitivity,
                specificity=m_no_bp.specificity,
                delta_auroc_from_baseline=round(m_no_bp.auroc - base_auroc, 4),
                delta_brier_from_baseline=round(m_no_bp.calibration.brier_score - base_brier, 4),
            )
        )

        # Resilience summary
        auroc_75 = rate_results[-1].auroc if rate_results else base_auroc
        retention = (auroc_75 / base_auroc * 100.0) if base_auroc > 0 else 0.0
        summary_text = (
            f"Under 75% synthetic feature missingness, the model retains {retention:.1f}% "
            f"of baseline discrimination (AUROC {auroc_75:.3f} vs baseline {base_auroc:.3f}). "
            f"Complete loss of laboratory panels incurs an AUROC change of {panel_results[0].delta_auroc_from_baseline:+.3f}."
        )

        return MissingDataSensitivityReport(
            baseline_auroc=base_auroc,
            baseline_brier=base_brier,
            rate_sensitivity_curve=rate_results,
            panel_dropout_evaluations=panel_results,
            resilience_summary=summary_text,
        )

    def _predict_from_raw(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms raw input through feature engineering and preprocessor, then predicts."""
        fe_df = self.feature_engineer.transform(df)
        drop_cols = ["patient_id", "event_outcome"]
        clean_df = fe_df.drop(columns=[c for c in drop_cols if c in fe_df.columns], errors="ignore")
        proc_df = self.preprocessor.transform(clean_df)
        return self.model.predict_proba(proc_df)[:, 1]
