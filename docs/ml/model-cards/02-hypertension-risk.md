# Model Card: Hypertension & Vascular Risk Model

## 1. Model Details
- **Model Name:** SevaHealth Hypertension & Vascular Risk Model
- **Identifier:** `ACC-AHA-ICMR-HTN-2017.v1`
- **Domain:** Essential Hypertension & Vascular Strain Risk Stratification
- **Model Type:** Multivariable Rule-Based Staging & Attribution Engine
- **Validation Status:** `CLINICALLY_VALIDATED`
- **Clinical Governance:** 2017 American College of Cardiology / American Heart Association (ACC/AHA) & ICMR Standard Treatment Workflows for Hypertension

## 2. Intended Use & Clinical Scope
- **Intended Purpose:** Identification of prehypertensive vascular elevation, Stage 1/Stage 2 hypertension, and hypertensive urgency during community screening.
- **Intended Users:** Primary Healthcare Workers, Community Nurses, Clinicians, and Screened Citizens.
- **Out-of-Scope:**
  - Emergency diagnosis of secondary hypertension (e.g. pheochromocytoma, renal artery stenosis).
  - Medication dosing or independent anti-hypertensive titration.

## 3. Clinical Provenance & Evidence Base
1. **2017 ACC/AHA/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults**: Whelton PK, et al. *J Am Coll Cardiol*. 2018;71(19):e127-e248.
2. **Indian Council of Medical Research (ICMR) Standard Treatment Workflows for Hypertension (2022)**: National non-communicable disease screening protocols under Ayushman Bharat Health and Wellness Centres.

## 4. Input Variables & Physiological Boundaries
| Input Feature | Canonical Unit | Mandatory? | Physiological Range | Clinical Staging Cutoff |
| :--- | :--- | :--- | :--- | :--- |
| `SYSTOLIC_BP` | mmHg | Yes | $[60, 280]$ | $< 120$ (Normal), $120-129$ (Elevated), $130-139$ (Stage 1), $\ge 140$ (Stage 2), $\ge 160$ (Critical) |
| `DIASTOLIC_BP` | mmHg | Yes | $[30, 160]$ | $< 80$ (Normal), $80-89$ (Stage 1), $\ge 90$ (Stage 2), $\ge 100$ (Critical) |
| `HEART_RATE` | beats/min | Optional | $[30, 240]$ | $> 90\text{ bpm}$ flags elevated sympathetic resting tone |
| `AGE` | years | Optional | $[1, 125]$ | Vascular stiffness cofactor |
| `SMOKING` | boolean | Optional | N/A | Accelerates acute and chronic vascular endothelial dysfunction |

## 5. Output Stratification
- **`LOW`** ($\text{Score} < 0.25$): $SBP < 120\text{ mmHg}$ and $DBP < 80\text{ mmHg}$.
- **`MODERATE`** ($0.25 \le \text{Score} < 0.70$): Elevated BP ($SBP\ 120-129$ and $DBP < 80$) or Stage 1 HTN ($SBP\ 130-139$ or $DBP\ 80-89$).
- **`HIGH`** ($\text{Score} \ge 0.70$): Stage 2 HTN ($SBP \ge 140$ or $DBP \ge 90$); scores $\ge 0.85$ indicate severe/critical elevation ($\ge 160/100\text{ mmHg}$).
- **`INSUFFICIENT_DATA`**: Neither SBP nor DBP provided. Model **NEVER assumes** a standard $120/80\text{ mmHg}$.

## 6. Algorithmic Explainability
- Assigns distinct feature-level drivers: "Stage 2 Severe Hypertension", "Stage 1 Elevated Pressure", "Tachycardia & Autonomic Strain".
- Detects protective normotension: "Optimal Arterial Pressure" with negative attribution weight.

## 7. Limitations & Caveats
- White-coat hypertension (clinic-induced transient elevation) may yield false positives in single-reading camp environments.
- Masked hypertension cannot be detected without 24-hour ambulatory blood pressure monitoring (ABPM) or home cuff logs.
- Single point-in-time cuff reading must be confirmed across two seated readings separated by $\ge 5$ minutes per ICMR protocol.

## 8. Clinical Safety Notice
> **SAFETY NOTICE: Risk estimation is NOT diagnosis.**
> A single blood pressure measurement does not establish chronic essential hypertension. Persistent elevation requires confirmatory clinical examination.
