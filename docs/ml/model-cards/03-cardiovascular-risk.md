# Model Card: Cardiovascular 10-Year ASCVD Risk Model

## 1. Model Details
- **Model Name:** SevaHealth 10-Year Atherosclerotic Cardiovascular Disease (ASCVD) Risk Model
- **Identifier:** `WHO-SEAR-ASCVD-2019.v1`
- **Domain:** Primary Prevention 10-Year Fatal and Non-Fatal ASCVD Probability
- **Model Type:** Multivariable Epidemiological Risk Stratification Engine
- **Validation Status:** `CLINICALLY_VALIDATED`
- **Clinical Governance:** World Health Organization (WHO) & WHO South-East Asia Regional Office (WHO-SEAR)

## 2. Intended Use & Clinical Scope
- **Intended Purpose:** Estimation of 10-year risk of major adverse cardiovascular events (myocardial infarction, coronary death, ischemic/hemorrhagic stroke) in individuals aged 40–74 years without established cardiovascular disease.
- **Intended Users:** Clinicians, Community Medical Officers, Primary Care Teams.
- **Out-of-Scope:**
  - Secondary prevention in patients with prior myocardial infarction, coronary stenting, CABG, or stroke.
  - Evaluation of pediatric or adolescent patients ($< 18$ years).

## 3. Clinical Provenance & Evidence Base
1. **WHO CVD Risk Chart Working Group:** *World Health Organization cardiovascular disease risk charts: 21 global regions to align with WHO 2019 guidelines*. Lancet Glob Health. 2019;7(10):e1332-e1345.
2. **South-East Asia Regional Charts (WHO-SEAR):** Calibrated specifically for Indian and South Asian populations exhibiting higher premature CAD incidence.

## 4. Input Variables & Physiological Boundaries
| Input Feature | Canonical Unit | Mandatory? | Physiological Range | Clinical Impact |
| :--- | :--- | :--- | :--- | :--- |
| `AGE` | years | Yes | $[1, 125]$ | Stratified across 40–49, 50–59, 60–69, 70+ brackets |
| `SYSTOLIC_BP` | mmHg | Yes | $[60, 280]$ | Primary continuous hemodynamics driver |
| `TOTAL_CHOLESTEROL`| mg/dL | Optional | $[50, 600]$ | Primary laboratory lipid driver ($< 160$ to $\ge 240\text{ mg/dL}$) |
| `SMOKING` | boolean | Optional | N/A | Current active tobacco use confers heavy risk multiplication |
| `SEX` | categorical | Optional | MALE / FEMALE | Sex-specific baseline hazard calibration |
| `BMI` | kg/m² | Optional | $[10, 90]$ | Validated non-laboratory proxy when total cholesterol is unavailable |

## 5. Non-Laboratory Primary Care Adaptation
In rural and community outreach camps lacking point-of-care total cholesterol testing, the model seamlessly transitions to the **WHO Non-Laboratory ASCVD Chart**, employing `BMI` as an adiposity surrogate. When this occurs, the model explicitly annotates:
`limitations: ["Total cholesterol missing; utilizing WHO non-laboratory BMI proxy."]` and adjusts confidence from $0.85$ down to $0.50-0.65$.

## 6. Output Stratification
- **`LOW`** ($\text{Score} < 0.20$): 10-year ASCVD risk $< 10\%$.
- **`MODERATE`** ($0.20 \le \text{Score} < 0.50$): 10-year ASCVD risk $10-19\%$.
- **`HIGH`** ($\text{Score} \ge 0.50$): 10-year ASCVD risk $\ge 20\%$ (warrants urgent clinical review and lipid-lowering therapy evaluation).
- **`INSUFFICIENT_DATA`**: Age or Systolic BP absent.

## 7. Limitations & Caveats
- Does not incorporate family history of premature CAD ($< 55$ years in first-degree relatives), which may necessitate higher clinical vigilance in South Asians.
- Does not account for Lipoprotein(a) or Coronary Artery Calcium (CAC) scoring.
- Calibrated for primary prevention only.

## 8. Clinical Safety Notice
> **SAFETY NOTICE: Risk estimation is NOT diagnosis.**
> 10-year ASCVD score is a statistical population risk forecast. It does not certify the presence or absence of coronary atherosclerosis.
