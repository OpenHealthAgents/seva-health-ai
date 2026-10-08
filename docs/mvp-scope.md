# SevaHealth AI: Minimum Viable Product (MVP) Scope & Evaluator Guide

**Document Version:** 1.0.0  
**Target:** Seva First Innovation Challenge (https://sevainnovationchallenge.in/)  
**Problem Statement:** Non-communicable and emerging lifestyle-oriented diseases  
**Core Success Metric:** A challenge evaluator can understand and verify the entire platform end-to-end within 5 minutes.

---

## 1. Executive Summary & Purpose

The purpose of the SevaHealth AI MVP is to prove that an AI-native preventive health platform can detect early, silent progression toward chronic lifestyle diseases, clearly explain what is driving the risk, formulate actionable 30-day lifestyle medicine interventions, monitor progress, and escalate dangerous trajectories to physicians—all within strict clinical safety boundaries.

The MVP does **NOT** attempt to be a generic wellness counter or an autonomous diagnosis bot. It is a **preventive-health decision-intelligence platform**.

---

## 2. Priority Disease & Risk Domains

In alignment with the challenge guidelines and national epidemiological priorities in India, the MVP focuses on four core interconnected NCD clusters:

| Priority Domain | Clinical Thresholds & Signals | Early Warning Value |
|---|---|---|
| **1. Diabetes & Prediabetes** | Fasting Blood Glucose 100-125 mg/dL; HbA1c 5.7%-6.4%; IDRS >= 60 | Detects pre-diabetes before irreversible beta-cell depletion. |
| **2. Hypertension** | Systolic BP 130-159 mmHg; Diastolic 85-99 mmHg (AHA/ACC Stage 1 & 2) | Identifies silent vascular damage before stroke or myocardial infarction. |
| **3. Cardiovascular Risk** | WHO/ISH 10-year CVD Risk Chart; Total Cholesterol > 200 mg/dL; Triglyceride/HDL ratio > 3.0 | Calculates composite vascular danger before ischemic events. |
| **4. Obesity & Metabolic Syndrome** | Asian Indian BMI >= 23 kg/m²; Waist >= 90cm (M) / >= 80cm (F); low HDL | Pinpoints central visceral adiposity driving systemic insulin resistance. |

*(Supported extensions: Chronic Kidney Disease via eGFR decline, and Metabolic Liver/NAFLD via FIB-4 index).*

---

## 3. The 8-Stage Core Loop Implementation

The platform executes the core loop continuously:

```
[SCREEN]       → Community screening (CBAC/IDRS), vitals capture, and wearable sync.
    ↓
[UNDERSTAND]   → Normalization against age, gender, and South Asian clinical cutoffs.
    ↓
[RISK STRATIFY]→ Deterministic guideline scoring (WHO-SEAR, ICMR) into tiers (Low, Mod, High, Critical).
    ↓
[PREDICT]      → Multivariable risk forecasting and 3-month trajectory trend calculation.
    ↓
[EXPLAIN]      → Feature attribution waterfall (+/- % contribution) with evidence citations.
    ↓
[INTERVENE]    → Personalized 30-day preventive lifestyle medicine care plan (Nutrition, Exercise, Sleep).
    ↓
[MONITOR]      → Daily habit completion tracking, wearable biometric trend monitoring.
    ↓
[ESCALATE]     → Clinician triage queue routing for critical vitals or worsening trajectory.
    ↓
[MEASURE]      → Population-level outcome tracking: "Did high intervention adherence lower BP & glucose?"
```

---

## 4. The 5-Minute Evaluator Journey (Demo Flow)

An evaluator exploring the platform can complete this end-to-end journey in under 5 minutes:

### Step 1: Select or Create a Citizen (0:00 - 0:45)
- Open the web application.
- Choose from 4 pre-loaded synthetic Indian personas representing distinct risk archetypes, or enter a new citizen profile.

### Step 2: Perform Screening & Enter Vitals (0:45 - 1:30)
- View the pre-populated Community Based Assessment Checklist (CBAC) and Indian Diabetes Risk Score (IDRS).
- Observe biometric vitals (Blood Pressure, Fasting Glucose, HbA1c, Waist Circumference).

### Step 3: Run AI NCD Risk Assessment (1:30 - 2:15)
- Trigger instant evaluation.
- View composite risk tier (e.g., **HIGH RISK: 68% Composite Index**).
- Inspect individual disease domain breakdowns:
  - Diabetes Risk: 74% (Prediabetic State)
  - Hypertension Risk: 62% (Stage 1)
  - Cardiovascular Risk: 45% (Moderate 10-yr risk)
  - Metabolic Syndrome: 70%

### Step 4: Examine Explainability Waterfall (2:15 - 3:00)
- View why risk is elevated through intuitive visual bars:
  - *+26% Elevated HbA1c (6.2%)*
  - *+19% Systolic Blood Pressure (138 mmHg)*
  - *+15% Sedentary Workstyle (< 30 min daily activity)*
  - *-10% Protective: Non-tobacco user*
- Notice the clear clinical disclaimer: **"Clinical review recommended. Not a medical diagnosis."**

### Step 5: Explore 30-Day Preventive Care Plan (3:00 - 3:45)
- Review the tailored lifestyle medicine roadmap broken down by week and day:
  - **Nutrition:** Low-glycemic fiber additions, sodium reduction to < 2g/day.
  - **Activity:** Post-meal 15-minute walks, 7,000 daily step goal.
  - **Sleep:** Consistent sleep schedule to reduce cortisol spikes.
- Check off a daily task and watch adherence update in real time.

### Step 6: Simulate Longitudinal Trajectory & Wearable Sync (3:45 - 4:15)
- Switch to longitudinal trend view showing 90-day trajectory.
- Click "Simulate Wearable Sync" to ingest synthetic smartwatch biometrics (Resting HR & HRV).

### Step 7: Open Clinician Triage Review (4:15 - 4:45)
- Switch to the **Clinician Portal**.
- View high-risk citizens flagged for clinical review.
- Inspect the AI-synthesized pre-consultation summary and preliminary SOAP draft.
- Act as the physician to click **"Approve Care Plan & Schedule Tele-Consult"**.

### Step 8: View Population-Level Impact (4:45 - 5:00)
- Switch to the **Public Health Administrator Portal**.
- Inspect district-level prevalence heatmaps (e.g., Mysuru, Bengaluru Rural, Hassan).
- Verify the **Outcome Efficacy Delta**: Demonstrates that citizens with >80% adherence experienced an average **0.4% HbA1c drop** and **6 mmHg Systolic BP reduction** over 30 days!

---

## 5. Realistic Synthetic Demo Personas

To respect privacy and regulatory standards, **zero real patient data** is used. Four comprehensive synthetic personas are seeded:

### Persona 1: Ramesh Patel (The Pre-Diabetic Urban Professional)
* **Age:** 48, Male, Software Architect (Bengaluru).
* **Clinical Baseline:** BMI 27.2 (Overweight), Waist 96 cm, Blood Pressure 138/88 mmHg, Fasting Glucose 118 mg/dL, HbA1c 6.2%, Sedentary desk job.
* **Risk Tier:** **HIGH RISK** (Prediabetes + Prehypertension + Metabolic Syndrome).
* **Trajectory:** Deteriorating (+12% risk increase over past 6 months).
* **Intervention Focus:** Glycemic load reduction, active workstation habits, brisk walking.

### Persona 2: Lakshmi Devi (The Rural Elder with Silent Hypertension)
* **Age:** 62, Female, Homemaker (Mandya District).
* **Clinical Baseline:** BMI 24.8, Waist 86 cm, Blood Pressure 164/98 mmHg (Stage 2 Hypertension), Fasting Glucose 96 mg/dL, HbA1c 5.5%, Family history of stroke.
* **Risk Tier:** **CRITICAL RISK** (Cardiovascular / Hypertensive Urgency).
* **Trajectory:** Deteriorating.
* **Escalation:** Immediate trigger for Community Health Worker (ASHA) home visit and Medical Officer triage.

### Persona 3: Vikram Singh (The High-Stress Transport Operator)
* **Age:** 39, Male, Long-distance Truck Driver.
* **Clinical Baseline:** BMI 28.6, Waist 102 cm, Blood Pressure 132/86 mmHg, Total Cholesterol 245 mg/dL, Triglycerides 280 mg/dL, Irregular sleep (5 hrs/night), Smoker (5 bidis/day).
* **Risk Tier:** **HIGH RISK** (Metabolic Syndrome + High ASCVD Risk).
* **Trajectory:** Stable-High.
* **Intervention Focus:** Tobacco cessation support, sleep regularity, dietary oil reduction.

### Persona 4: Priya Sharma (The Active Baseline)
* **Age:** 29, Female, Teacher (Mysuru).
* **Clinical Baseline:** BMI 21.2, Waist 74 cm, Blood Pressure 116/74 mmHg, Fasting Glucose 84 mg/dL, HbA1c 5.1%, 8,500 daily steps.
* **Risk Tier:** **LOW RISK** (Healthy physiological baseline).
* **Trajectory:** Stable.
* **Intervention Focus:** Sustained preventive maintenance and annual screening.

---

## 6. Execution & Verification Environment

The MVP is engineered to run in two frictionless modes:
1. **Containerized Production-like Mode:** Full multi-container stack via `docker compose up` (FastAPI backend, Next.js web portal, PostgreSQL, Redis, MinIO).
2. **Instant Developer / Evaluator Mode:** Standalone FastAPI server with embedded SQLite persistence and deterministic local mock LLM fallback—runnable with a single command without Docker or external cloud keys required.
