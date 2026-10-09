# Model Card: calibrated_gradient_boosting_risk_model

| Version Attribute | Version String |
|---|---|
| **Model Version** | `v1.0.0` |
| **Training Data Version** | `v1.0.0` |
| **Feature Version** | `v1.0.0` |
| **Evaluation Version** | `v1.0.0` |
| **Release Date** | 2026-10-09 |

---

> ⚠️ **REGULATORY & CLINICAL VALIDATION DISCLAIMER**
> 
> DO NOT CLAIM CLINICAL VALIDATION. This model is a research prototype developed for decision-support exploration in community screening settings. It has NOT undergone clinical trials, has not received regulatory clearance (such as FDA 510(k), CE-IVD, or CDSCO MD-42), and is strictly prohibited from autonomous clinical triage, acute diagnosis, or medication dosing.

---

## 1. Intended Use
- **Primary Purpose**: Demonstration early-warning cardiometabolic risk stratification for community health screenings.
- **Target Users**: Community Health Workers (ASHAs), Primary Care Nurses, Preventive Health Officers
- **Intended Care Setting**: Community primary health centers and rural screening camps.

### Out-of-Scope & Prohibited Uses
- ⛔ Autonomous diagnosis of acute coronary syndrome or stroke.
- ⛔ Automated prescription or alteration of anti-hypertensive or anti-diabetic medication.
- ⛔ Standalone clinical decision-making without physician oversight.

## 2. Target Population & Cohort Demographics
- **Target Age Range**: 18 to 85 years
- **Regional Representation**: North-Rural, North-Urban, South-Rural, South-Urban, East-Rural, East-Urban, West-Rural, West-Urban
- **Disease Prevalence in Cohort**: 5.8% positive event rate in cohort
- **Inclusion Criteria**: Adults participating in preventive cardiometabolic health screening.
- **Exclusion Criteria**: Active emergency symptoms (chest pain, shock), pregnancy, pediatric population (<18y).

## 3. Model Inputs & Engineered Features
Total input features: **24**

```
age, sex, demographic_group, bmi, systolic_bp, diastolic_bp, heart_rate, fasting_glucose, hba1c, total_cholesterol, hdl_cholesterol, ldl_cholesterol, triglycerides, serum_creatinine, smoking_status, physical_activity, family_history, mean_arterial_pressure, pulse_pressure, cholesterol_hdl_ratio, triglyceride_hdl_ratio, hypertension_stage, glycemic_risk_flag, metabolic_syndrome_score
```

## 4. Quantitative Performance Metrics
### Overall Test Set Metrics
| Metric | Value |
|---|---|
| Auroc | 0.7554 |
| Auprc | 0.1737 |
| Sensitivity | 0.0000 |
| Specificity | 1.0000 |
| Ppv | 0.0000 |
| Npv | 0.9425 |
| Brier Score | 0.0522 |
| Expected Calibration Error | 0.0200 |
| Optimal Threshold | 0.0500 |

### Demographic Disparity & Fairness
- **Sex Max Auroc Difference**: `0.1455`
- **Sex Equal Opportunity Diff**: `0.0`
- **Sex Demographic Parity Diff**: `0.0`
- **Age Max Auroc Difference**: `0.1996`
- **Demographic Group Max Auroc Difference**: `0.359`

### Missing-Data Sensitivity
- **Missingness Robustness**: Under 75% synthetic feature missingness, the model retains 93.4% of baseline discrimination (AUROC 0.706 vs baseline 0.755). Complete loss of laboratory panels incurs an AUROC change of -0.033.

## 5. Model Limitations
- ⚠️ Trained and evaluated on synthetic demonstration cohorts simulating epidemiological distributions.
- ⚠️ Does NOT incorporate serial ECG waveforms, continuous telemetry, or genomic polygenic risk scores.
- ⚠️ Laboratory biomarker imputation assumes missingness patterns observed in demonstration data; extreme unmeasured covariates may degrade accuracy.
- ⚠️ Predictions reflect statistical risk association rather than causal individual pathophysiology.

## 6. Known Risks & Ethical Considerations
- ❗ Risk of False Negatives: Patient with atypical presentation may receive Low Risk rating, delaying clinical referral.
- ❗ Risk of False Positives: Healthy patient flagged as High Risk may experience psychological distress and unnecessary secondary care referral.
- ❗ Demographic Disparity: Resource-constrained rural clinics lacking point-of-care lab tests will experience moderate sensitivity drop.
- ❗ Over-reliance / Automation Bias: Clinicians must not treat risk scores as definitive diagnostic findings.

## 7. Model Governance & Maintenance Plan
- **Retraining Frequency**: Bi-annual or when data distribution drift exceeds PSI > 0.25.
- **Drift Monitoring**: Continuous tracking of mean arterial pressure distribution and lab testing availability.
- **Human-in-the-Loop Requirement**: All flagged high-risk alerts must be validated by a registered medical officer.