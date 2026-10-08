# SevaHealth AI: Clinical Risk Model Cards Catalog

This catalog documents the mathematical specifications, clinical provenance, physiological boundaries, and explainability mechanisms of the **SevaHealth AI NCD Risk Engine**.

## Architectural Principles
1. **Risk Estimation is NOT Diagnosis:** Output probabilistic risk and guideline staging, never autonomous clinical diagnoses.
2. **Clinical Provenance First:** Models ground themselves in peer-reviewed national and international guidelines (ICMR, WHO, ACC/AHA, KDIGO).
3. **No Silent Data Imputation:** Missing mandatory fields produce `INSUFFICIENT_DATA` rather than silent substitution of normal defaults.
4. **Physiological Guardrails:** Biometrics outside biological possibility ($SBP > 280\text{ mmHg}$, $Glucose > 600\text{ mg/dL}$, etc.) raise `PhysiologicalValidationError`.
5. **Transparent Heuristic Demarcation:** Non-validated demo algorithms are explicitly tagged `DEMONSTRATION ONLY`.

---

## Model Inventory

| Domain | Model Identifier | Provenance & Authority | Validation Status | Mandatory Inputs |
| :--- | :--- | :--- | :--- | :--- |
| **Diabetes & Glycemic** | [`ICMR-INDIAB-IDRS-2023.v1`](01-diabetes-metabolic-risk.md) | ICMR Guidelines 2023 / IDRS (Mohan et al.) | `CLINICALLY_VALIDATED` | `AGE` |
| **Hypertension & Vascular** | [`ACC-AHA-ICMR-HTN-2017.v1`](02-hypertension-risk.md) | 2017 ACC/AHA Guidelines / ICMR Protocol | `CLINICALLY_VALIDATED` | `SYSTOLIC_BP`, `DIASTOLIC_BP` |
| **Cardiovascular ASCVD** | [`WHO-SEAR-ASCVD-2019.v1`](03-cardiovascular-risk.md) | WHO South-East Asia Region 10-Yr Charts | `CLINICALLY_VALIDATED` | `AGE`, `SYSTOLIC_BP` |
| **Obesity & Metabolic** | [`WHO-ICMR-METABOLIC-2023.v1`](04-obesity-metabolic-risk.md) | WHO South Asian BMI Cutoff / ICMR Central Adiposity | `CLINICALLY_VALIDATED` | `WAIST_CIRCUMFERENCE`, `BMI` (or `H`+`W`) |
| **Chronic Kidney Disease** | [`KDIGO-CKD-EPI-2024.v1`](05-ckd-risk.md) | KDIGO 2024 Guideline / CKD-EPI 2021 Equation | `CLINICALLY_VALIDATED` (Biomarker) / `DEMONSTRATION_ONLY` (Heuristic) | `EGFR` or `SERUM_CREATININE` (or comorbidities for Demo) |

---

## Detailed Model Cards
- [01. Diabetes & Glycemic Risk Model](01-diabetes-metabolic-risk.md)
- [02. Hypertension & Vascular Risk Model](02-hypertension-risk.md)
- [03. Cardiovascular 10-Year ASCVD Risk Model](03-cardiovascular-risk.md)
- [04. South Asian Obesity & Metabolic Syndrome Model](04-obesity-metabolic-risk.md)
- [05. Chronic Kidney Disease (CKD) Model](05-ckd-risk.md)
