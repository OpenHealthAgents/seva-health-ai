# Model Card: Diabetes & Glycemic Risk Model

## 1. Model Details
- **Model Name:** SevaHealth Diabetes & Glycemic Risk Model
- **Identifier:** `ICMR-INDIAB-IDRS-2023.v1`
- **Domain:** Type 2 Diabetes Mellitus & Prediabetes Risk Stratification
- **Model Type:** Multivariable Rule-Based & Logistic Attribution Engine
- **Validation Status:** `CLINICALLY_VALIDATED`
- **Clinical Governance:** Indian Council of Medical Research (ICMR) & Madras Diabetes Research Foundation (MDRF)

## 2. Intended Use & Clinical Scope
- **Intended Purpose:** Opportunistic population screening and early-warning detection of impaired fasting glycemia, prediabetes, and undiagnosed Type 2 Diabetes Mellitus in Indian adults ($\ge 18$ years).
- **Intended Users:** Primary Healthcare Workers (ASHA/ANM), Primary Care Physicians, and Citizens reviewing self-screening results.
- **Out-of-Scope:**
  - Independent clinical diagnosis of Diabetes Mellitus.
  - Evaluation of gestational diabetes during pregnancy.
  - Management of acute diabetic ketoacidosis (DKA) or hyperosmolar hyperglycemic state (HHS).

## 3. Clinical Provenance & Evidence Base
1. **ICMR Guidelines for Management of Type 2 Diabetes (2023):** Diagnostic thresholds for impaired fasting glucose ($\ge 100\text{ mg/dL}$), impaired glucose tolerance, and diabetic thresholds ($HbA1c \ge 6.5\%$ or $FBG \ge 126\text{ mg/dL}$).
2. **Indian Diabetes Risk Score (IDRS):** Mohan V, et al. *A simplified Indian Diabetes Risk Score (IDRS) for screening for undiagnosed diabetic subjects in South Indians (CURES-24)*. J Assoc Physicians India. 2005;53:759-763.
3. **ICMR-INDIAB Study:** Anjana RM, et al. *Metabolic non-communicable disease health report in India*. Lancet Diabetes Endocrinol. 2023;11(7):474-489.

## 4. Input Variables & Physiological Boundaries
| Input Feature | Canonical Unit | Mandatory? | Physiological Range | Clinical Cutoff / Attribution Trigger |
| :--- | :--- | :--- | :--- | :--- |
| `AGE` | years | Yes | $[1, 125]$ | $< 35\text{ yrs} (0\text{ pts}), 35-49\text{ yrs} (20\text{ pts}), \ge 50\text{ yrs} (30\text{ pts})$ |
| `HBA1C` | % | Optional | $[3.0, 20.0]$ | $< 5.7\%$ (Normal), $5.7-6.4\%$ (Prediabetes), $\ge 6.5\%$ (Diabetes) |
| `FASTING_GLUCOSE` | mg/dL | Optional | $[35, 600]$ | $< 100\text{ mg/dL}$ (Normal), $100-125\text{ mg/dL}$ (IFG), $\ge 126\text{ mg/dL}$ (Diabetes) |
| `WAIST_CIRCUMFERENCE` | cm | Optional | $[40, 180]$ | Male: $\ge 90\text{ cm}$; Female: $\ge 80\text{ cm}$ (Asian Indian criteria) |
| `PHYSICAL_ACTIVITY` | category | Optional | N/A | Vigorous/Strenuous (0 pts), Moderate (10 pts), Sedentary (20 pts) |
| `FAMILY_HISTORY` | category | Optional | N/A | No parent (0 pts), One parent (10 pts), Both parents (20 pts) |
| `IDRS_SCORE` | points | Optional | $[0, 100]$ | $< 30$ (Low), $30-50$ (Moderate), $\ge 60$ (High Risk) |

## 5. Output Stratification
- **`LOW`** ($\text{Score} < 0.25$): Fasting glycemia normal, IDRS $< 30$. Protective factors credited.
- **`MODERATE`** ($0.25 \le \text{Score} < 0.70$): Impaired Fasting Glucose ($100-125\text{ mg/dL}$), $HbA1c\ 5.7-6.4\%$, or IDRS $30-59$.
- **`HIGH`** ($\text{Score} \ge 0.70$): $HbA1c \ge 6.5\%$, $FBG \ge 126\text{ mg/dL}$, or IDRS $\ge 60$ with abdominal adiposity.
- **`INSUFFICIENT_DATA`**: Age or baseline clinical observations absent. Missing values are **NEVER silently substituted**.

## 6. Algorithmic Explainability
The model generates deterministic, feature-level attribution weights adhering to:
- Positive contributions (`INCREASES_RISK`): Biometric markers exceeding guideline thresholds.
- Negative contributions (`DECREASES_RISK`): Normoglycemic biomarkers and cardioprotective lifestyle habits.

## 7. Limitations & Caveats
- Point-of-care capillary glucometers have $\pm 15\%$ analytical variation compared to venous hexokinase assays.
- Variant hemoglobins (e.g., HbS, HbE, beta-thalassemia trait prevalent in Indian tribal regions) can falsely lower or raise HbA1c readings.
- Oral glucose tolerance test (OGTT 2h post-75g) is not performed in community screening, which may miss isolated impaired glucose tolerance.

## 8. Clinical Safety Notice
> **SAFETY NOTICE: Risk estimation is NOT diagnosis.**
> This score represents statistical probability and clinical screening guidelines. It does not replace a physician's diagnostic evaluation or laboratory venous blood tests.
