"""Core clinical performance metrics: discrimination, calibration, and classification.

Metrics:
- AUROC (Area under ROC curve)
- AUPRC (Area under Precision-Recall curve)
- Sensitivity (Recall / True Positive Rate)
- Specificity (True Negative Rate)
- PPV (Positive Predictive Value / Precision)
- NPV (Negative Predictive Value)
- Calibration: ECE (Expected Calibration Error), MCE (Max Calibration Error),
  Calibration curve points, slope and intercept
- Brier score
- Confusion matrix (TP, FP, TN, FN)

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)


@dataclass
class ConfusionMatrixValues:
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    total: int


@dataclass
class CalibrationMetrics:
    brier_score: float
    expected_calibration_error: float
    max_calibration_error: float
    prob_true: List[float]
    prob_pred: List[float]
    calibration_slope: float
    calibration_intercept: float


@dataclass
class ClinicalEvaluationMetrics:
    auroc: float
    auprc: float
    sensitivity: float
    specificity: float
    ppv: float
    npv: float
    accuracy: float
    f1_score: float
    decision_threshold: float
    confusion_matrix: ConfusionMatrixValues
    calibration: CalibrationMetrics
    prevalence: float
    num_samples: int
    disclaimer: str = (
        "RESEARCH DEMONSTRATION ONLY: Metrics computed on demonstration dataset. "
        "These performance metrics do not constitute clinical validation."
    )


class ClinicalMetricsCalculator:
    """Calculates comprehensive discrimination and calibration metrics for clinical models."""

    @staticmethod
    def compute_all_metrics(
        y_true: Union[np.ndarray, List[int]],
        y_prob: Union[np.ndarray, List[float]],
        threshold: float = 0.5,
        n_bins: int = 10,
    ) -> ClinicalEvaluationMetrics:
        """Compute all required metrics."""
        y_true_arr = np.asarray(y_true, dtype=int)
        y_prob_arr = np.asarray(y_prob, dtype=float)

        # Basic counts
        n_samples = len(y_true_arr)
        prevalence = float(np.mean(y_true_arr))

        # 1. Discrimination (AUROC and AUPRC)
        if len(np.unique(y_true_arr)) > 1:
            auroc = float(roc_auc_score(y_true_arr, y_prob_arr))
            auprc = float(average_precision_score(y_true_arr, y_prob_arr))
        else:
            auroc = float("nan")
            auprc = float("nan")

        # 2. Confusion matrix at threshold
        y_pred = (y_prob_arr >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true_arr, y_pred, labels=[0, 1]).ravel()
        cm = ConfusionMatrixValues(
            true_positives=int(tp),
            false_positives=int(fp),
            true_negatives=int(tn),
            false_negatives=int(fn),
            total=n_samples,
        )

        # 3. Clinical Diagnostic Rates
        # Sensitivity = TP / (TP + FN)
        sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        # Specificity = TN / (TN + FP)
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        # PPV = TP / (TP + FP)
        ppv = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        # NPV = TN / (TN + FN)
        npv = float(tn / (tn + fn)) if (tn + fn) > 0 else 0.0
        # Accuracy
        accuracy = float((tp + tn) / n_samples) if n_samples > 0 else 0.0
        # F1 Score
        f1_score = (
            float(2 * (ppv * sensitivity) / (ppv + sensitivity))
            if (ppv + sensitivity) > 0
            else 0.0
        )

        # 4. Calibration Metrics
        brier = float(brier_score_loss(y_true_arr, y_prob_arr))

        # Reliability curve (binning)
        prob_true, prob_pred = calibration_curve(
            y_true_arr,
            y_prob_arr,
            n_bins=n_bins,
            strategy="uniform",
        )

        # Expected Calibration Error (ECE) and Max Calibration Error (MCE)
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0
        mce = 0.0
        for i in range(n_bins):
            in_bin = (y_prob_arr >= bin_edges[i]) & (y_prob_arr < bin_edges[i + 1])
            if i == n_bins - 1:
                in_bin = (y_prob_arr >= bin_edges[i]) & (y_prob_arr <= bin_edges[i + 1])
            count = np.sum(in_bin)
            if count > 0:
                bin_acc = np.mean(y_true_arr[in_bin])
                bin_conf = np.mean(y_prob_arr[in_bin])
                diff = abs(bin_acc - bin_conf)
                ece += (count / n_samples) * diff
                if diff > mce:
                    mce = diff

        # Calibration slope and intercept (logistic regression of y on logit(p))
        eps = 1e-6
        clipped_p = np.clip(y_prob_arr, eps, 1.0 - eps)
        logits = np.log(clipped_p / (1.0 - clipped_p))

        try:
            from sklearn.linear_model import LogisticRegression
            cal_reg = LogisticRegression(solver="lbfgs")
            cal_reg.fit(logits.reshape(-1, 1), y_true_arr)
            slope = float(cal_reg.coef_[0][0])
            intercept = float(cal_reg.intercept_[0])
        except Exception:
            slope = 1.0
            intercept = 0.0

        cal_metrics = CalibrationMetrics(
            brier_score=round(brier, 4),
            expected_calibration_error=round(float(ece), 4),
            max_calibration_error=round(float(mce), 4),
            prob_true=[round(float(x), 4) for x in prob_true],
            prob_pred=[round(float(x), 4) for x in prob_pred],
            calibration_slope=round(slope, 3),
            calibration_intercept=round(intercept, 3),
        )

        return ClinicalEvaluationMetrics(
            auroc=round(auroc, 4),
            auprc=round(auprc, 4),
            sensitivity=round(sensitivity, 4),
            specificity=round(specificity, 4),
            ppv=round(ppv, 4),
            npv=round(npv, 4),
            accuracy=round(accuracy, 4),
            f1_score=round(f1_score, 4),
            decision_threshold=threshold,
            confusion_matrix=cm,
            calibration=cal_metrics,
            prevalence=round(prevalence, 4),
            num_samples=n_samples,
        )

    @staticmethod
    def find_optimal_threshold(
        y_true: np.ndarray,
        y_prob: np.ndarray,
        metric: str = "youden",  # "youden" (sens+spec-1) or "f1"
    ) -> float:
        """Finds optimal decision threshold balancing clinical sensitivity and specificity."""
        thresholds = np.linspace(0.05, 0.95, 91)
        best_score = -1.0
        best_thresh = 0.5

        for th in thresholds:
            y_pred = (y_prob >= th).astype(int)
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
            sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0

            if metric == "youden":
                score = sens + spec - 1.0
            elif metric == "f1":
                score = 2 * (prec * sens) / (prec + sens) if (prec + sens) > 0 else 0.0
            else:
                score = sens

            if score > best_score:
                best_score = score
                best_thresh = float(th)

        return round(best_thresh, 3)
