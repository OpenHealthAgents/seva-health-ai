# Clinical Model Evaluation Report: calibrated_gradient_boosting_risk_model (v1.0.0)

> ⚠️ **IMPORTANT DISCLAIMER**: For research and demonstration purposes only. This model and evaluation do **NOT** claim clinical validation. Not cleared for medical diagnostic use.

## 1. Version Lineage & Provenance
- **Model Version**: `v1.0.0`
- **Training Data Version**: `v1.0.0`
- **Feature Version**: `v1.0.0`
- **Evaluation Version**: `v1.0.0`
- **Evaluation Timestamp**: `2026-10-09T08:32:07.483566`
- **Evaluated Samples**: 400 (Prevalence: 5.8%)

## 2. Core Clinical Performance Metrics
| Metric | Value | Interpretation / Goal |
|---|---|---|
| **AUROC** | **0.7554** | Discrimination (Area under ROC) |
| **AUPRC** | **0.1737** | Precision-Recall curve area |
| **Sensitivity (Recall)** | **0.00%** | True Positive Rate at threshold 0.50 |
| **Specificity** | **100.00%** | True Negative Rate at threshold 0.50 |
| **PPV (Precision)** | **0.00%** | Positive Predictive Value |
| **NPV** | **94.25%** | Negative Predictive Value |
| **Brier Score** | **0.0522** | Overall calibration error (lower is better) |
| **Expected Calib. Error (ECE)** | **0.0200** | Probability reliability gap |
| **Max Calib. Error (MCE)** | **0.5849** | Maximum reliability gap |
| **Calibration Slope** | **0.644** | Target ~1.0 |
| **Calibration Intercept** | **-0.835** | Target ~0.0 |
| **Optimal Threshold (Youden's J)** | **0.050** | Optimized for balanced sensitivity/specificity |

### Confusion Matrix (Threshold = 0.50)
| | Actual Positive | Actual Negative |
|---|---|---|
| **Predicted Positive** | TP: **0** | FP: **0** |
| **Predicted Negative** | FN: **23** | TN: **377** |

## 3. Subgroup Performance & Demographic Equity
### Performance by Sex
| Sex | N | Prevalence | AUROC | Sensitivity | Specificity | PPV | NPV | Brier |
|---|---|---|---|---|---|---|---|---|
| Female | 198 | 3.0% | 0.8485 | 0.0% | 100.0% | 0.0% | 97.0% | 0.0299 |
| Male | 202 | 8.4% | 0.7030 | 0.0% | 100.0% | 0.0% | 91.6% | 0.0740 |

### Performance by Age Bracket
| Age Bracket | N | Prevalence | AUROC | Sensitivity | Specificity | PPV | NPV | Brier |
|---|---|---|---|---|---|---|---|---|
| 40-54 | 129 | 3.1% | 0.6670 | 0.0% | 100.0% | 0.0% | 96.9% | 0.0306 |
| 55-69 | 105 | 9.5% | 0.7089 | 0.0% | 100.0% | 0.0% | 90.5% | 0.0813 |
| 70+ | 53 | 13.2% | 0.5093 | 0.0% | 100.0% | 0.0% | 86.8% | 0.1213 |
| <40 | 113 | 1.8% | 0.5608 | 0.0% | 100.0% | 0.0% | 98.2% | 0.0174 |

### Performance by Demographic / Regional Cohort
| Demographic Group | N | Prevalence | AUROC | Sensitivity | Specificity | PPV | NPV |
|---|---|---|---|---|---|---|---|
| East-Rural | 54 | 5.6% | 0.7680 | 0.0% | 100.0% | 0.0% | 94.4% |
| East-Urban | 61 | 6.6% | 0.6206 | 0.0% | 100.0% | 0.0% | 93.4% |
| North-Rural | 43 | 14.0% | 0.7230 | 0.0% | 100.0% | 0.0% | 86.1% |
| North-Urban | 51 | 3.9% | 0.9796 | 0.0% | 100.0% | 0.0% | 96.1% |
| South-Rural | 41 | 2.4% | 0.9250 | 0.0% | 100.0% | 0.0% | 97.6% |
| South-Urban | 40 | 2.5% | 0.8718 | 0.0% | 100.0% | 0.0% | 97.5% |
| West-Rural | 61 | 4.9% | 0.7155 | 0.0% | 100.0% | 0.0% | 95.1% |
| West-Urban | 49 | 6.1% | 0.7790 | 0.0% | 100.0% | 0.0% | 93.9% |

### Fairness & Disparity Summary
- **Sex Max Auroc Difference**: `0.1455`
- **Sex Equal Opportunity Diff**: `0.0`
- **Sex Demographic Parity Diff**: `0.0`
- **Age Max Auroc Difference**: `0.1996`
- **Demographic Group Max Auroc Difference**: `0.359`

## 4. Missing-Data Sensitivity & Degradation Curve
> Under 75% synthetic feature missingness, the model retains 93.4% of baseline discrimination (AUROC 0.706 vs baseline 0.755). Complete loss of laboratory panels incurs an AUROC change of -0.033.

### Performance Under Increasing Feature Missingness Rates
| Condition | Simulated Missing Rate | AUROC | Δ AUROC | Brier Score | Sensitivity | Specificity |
|---|---|---|---|---|---|---|
| Baseline (Observed) | 0.0% | 0.7554 | 0.0000 | 0.0522 | 0.0% | 100.0% |
| Random Missing 10% | 10% | 0.7638 | +0.0084 | 0.0513 | 0.0% | 100.0% |
| Random Missing 25% | 25% | 0.7400 | -0.0154 | 0.0532 | 0.0% | 100.0% |
| Random Missing 40% | 40% | 0.7501 | -0.0053 | 0.0533 | 0.0% | 100.0% |
| Random Missing 60% | 60% | 0.7375 | -0.0179 | 0.0523 | 0.0% | 100.0% |
| Random Missing 75% | 75% | 0.7058 | -0.0496 | 0.0557 | 0.0% | 100.0% |

### Clinical Panel Dropouts (Point-of-Care Resource Constraints)
| Panel Dropout Scenario | AUROC | Δ AUROC | Brier Score | Sensitivity | Specificity |
|---|---|---|---|---|---|
| No Laboratory Tests (Point-of-Care Unavailable) | 0.7221 | -0.0333 | 0.0531 | 0.0% | 100.0% |
| No Blood Pressure Cuff | 0.7172 | -0.0382 | 0.0532 | 0.0% | 100.0% |

## 5. Non-Clinical Validation Affirmation
RESEARCH DEMONSTRATION ONLY: This evaluation report reflects simulated performance on synthetic cohorts. The model and metrics are NOT clinically validated and must not be used for unsupervised clinical decision-making or diagnostic claims.