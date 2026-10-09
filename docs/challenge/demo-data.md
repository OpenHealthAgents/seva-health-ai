# SevaHealth AI — Synthetic Demonstration Personas & Cohorts

> **Data Policy**: 100% Synthetic Demonstration Data — Zero Real Patient Data (HIPAA / DISHA Compliant)  
> **Seeding Command**: `python scripts/seed_data.py` (Automatically invoked via `make demo`)

---

## 1. The Twelve Synthetic Clinical Personas

The platform includes twelve fully articulated synthetic clinical personas designed to demonstrate the complete spectrum of NCD phenotypes:

| # | Persona Name | Age / Sex | Clinical Phenotype / Narrative | Baseline Risk Tier | Longitudinal Trajectory |
|:---:|:---|:---:|:---|:---:|:---:|
| **1** | **Ramesh Patel** | 52 / M | Sedentary schoolteacher with borderline blood sugar drifting into diabetes | **MODERATE** | **DETERIORATING** (Reversible) |
| **2** | **Sunita Sharma** | 44 / F | Working mother with early prediabetes and chronic sleep deficit | **MODERATE** | **IMPROVING** |
| **3** | **Vikram Mehta** | 38 / M | High-stress tech professional with accelerating hypertensive spikes | **HIGH** | **DETERIORATING** |
| **4** | **Lakshmi Devi** | 68 / F | Elderly rural grandmother with Stage 2 hypertension & isolated systolic drift | **HIGH** | **CRITICAL / EMERGENT** |
| **5** | **Priya Nair** | 29 / F | Young professional with healthy active lifestyle, wearable step tracker | **LOW** | **STABLE** |
| **6** | **Rajesh Kumar** | 58 / M | Shopkeeper with high cardiovascular risk and elevated non-HDL cholesterol | **HIGH** | **DETERIORATING** |
| **7** | **Amit Verma** | 47 / M | Recovering metabolic syndrome citizen who completed 30-day care plan | **MODERATE** | **IMPROVING** |
| **8** | **Meena Patil** | 61 / F | Rural agricultural worker with emerging CKD and diabetic proteinuria | **HIGH** | **HIGH RISK / MONITOR** |
| **9** | **Anand Joshi** | 33 / M | Sedentary young adult with BMI 31.2, nocturnal heart rate variability dip | **MODERATE** | **DETERIORATING** |
| **10**| **Kavitha Rao** | 54 / F | Multiple-risk citizen (Metabolic + Cardiac + Stress) with complex comorbidities | **HIGH** | **HIGH RISK** |
| **11**| **Suresh Gowda** | 41 / M | Farmer with tobacco use and borderline Stage 1 hypertension | **MODERATE** | **STABLE** |
| **12**| **Devendra Sharma** | 52 / M | Canonical 16-step challenge evaluation persona (drifts then reverses) | **MODERATE** | **REVERSED (-72%)** |

---

## 2. Ingested Biomarker & Telemetry Profiles

Every synthetic persona carries a rich, multi-layered clinical history:
- **Biometric Vitals**: Systolic/diastolic BP, resting pulse, waist circumference, BMI.
- **Laboratory Chemistry**: HbA1c (%), fasting capillary/venous glucose (mg/dL), serum creatinine (mg/dL), lipid profile.
- **Continuous Wearables (Open Wearables)**: 14 to 30 days of daily steps, sleep duration, deep sleep percentage, and resting heart rate.
- **Structured Care Plans**: Multi-pillar nutrition, movement, and habit schedules with recorded adherence checklists.
- **Clinical Triage Cases**: Pre-compiled SOAP clinical case summaries ready for physician review in the Clinician Copilot.
