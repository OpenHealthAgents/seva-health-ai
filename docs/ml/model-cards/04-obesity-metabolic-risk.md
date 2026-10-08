# Model Card: Obesity & Metabolic Syndrome Risk Model

## 1. Model Details
- **Model Name:** SevaHealth South Asian Obesity & Metabolic Syndrome Risk Model
- **Identifier:** `WHO-ICMR-METABOLIC-2023.v1`
- **Domain:** Visceral Adiposity, Sarcopenic Obesity, and Metabolic Syndrome
- **Model Type:** Multivariable Anthropometric & Dyslipidemia Attribution Engine
- **Validation Status:** `CLINICALLY_VALIDATED`
- **Clinical Governance:** WHO Expert Consultation on South Asian BMI & ICMR Consensus on Central Obesity in Indians

## 2. Intended Use & Clinical Scope
- **Intended Purpose:** Identification of central (visceral) adiposity, overweight/obesity under Asian Indian specific cutoffs, and atherogenic dyslipidemia.
- **Intended Users:** Primary Health Workers, Wellness Coaches, Physicians, Citizens.
- **Key Clinical Rationale:** Asian Indians possess a distinct **"Thin-Fat Phenotype"** characterized by normal or borderline BMI but excessive intra-abdominal visceral adipose tissue, severe insulin resistance, and premature cardiometabolic disease. Caucasian BMI cutoffs (overweight $\ge 25$, obese $\ge 30$) systematically underdiagnose high-risk Indian individuals.

## 3. Clinical Provenance & Evidence Base
1. **WHO Expert Consultation:** *Appropriate body-mass index for Asian populations and its implications for policy and intervention strategies*. Lancet. 2004;363(9403):157-163.
2. **ICMR / Misra et al. Consensus:** Misra A, et al. *Consensus physical activity, nutrition, and lifestyle guidelines for Asian Indians in management of obesity, metabolic syndrome, and diabetes*. J Assoc Physicians India. 2009;57:163-170.
3. **Harmonized Metabolic Syndrome Definition:** Alberti KG, et al. *Harmonizing the metabolic syndrome*. Circulation. 2009;120(16):1640-1645.

## 4. Input Variables & Physiological Boundaries
| Input Feature | Canonical Unit | Mandatory? | Physiological Range | South Asian Clinical Thresholds |
| :--- | :--- | :--- | :--- | :--- |
| `WAIST_CIRCUMFERENCE` | cm | Yes | $[40, 180]$ | Men: $\ge 90\text{ cm}$; Women: $\ge 80\text{ cm}$ (Primary marker of central adiposity) |
| `BMI` | kg/m² | Yes (or H+W) | $[10, 90]$ | $< 23$ (Normal), $23.0-24.9$ (Overweight), $\ge 25.0$ (Obesity) |
| `TRIGLYCERIDES` | mg/dL | Optional | $[30, 1200]$ | $\ge 150\text{ mg/dL}$ (Hypertriglyceridemia) |
| `HDL_CHOLESTEROL` | mg/dL | Optional | $[10, 150]$ | Men: $< 40\text{ mg/dL}$; Women: $< 50\text{ mg/dL}$ (Atherogenic dyslipidemia) |
| `FASTING_GLUCOSE` | mg/dL | Optional | $[35, 600]$ | $\ge 100\text{ mg/dL}$ (Impaired fasting glucose) |

## 5. Output Stratification
- **`LOW`** ($\text{Score} < 0.25$): $BMI < 23\text{ kg/m²}$, Waist $< 90\text{ cm}$ (men) / $< 80\text{ cm}$ (women).
- **`MODERATE`** ($0.25 \le \text{Score} < 0.60$): $BMI\ 23.0-24.9\text{ kg/m²}$ (Overweight) OR isolated elevated waist circumference.
- **`HIGH`** ($\text{Score} \ge 0.60$): $BMI \ge 25.0\text{ kg/m²}$ (Obese by Indian criteria) AND Central Adiposity with atherogenic lipid co-factors.
- **`INSUFFICIENT_DATA`**: Neither waist circumference nor BMI (or height + weight) provided.

## 6. Algorithmic Explainability
- Attributes visceral adiposity separately from general BMI.
- Flags "Thin-Fat Phenotype" if waist circumference is elevated despite normal BMI ($< 23\text{ kg/m²}$).
- Identifies atherogenic dyslipidemia when high triglycerides coincide with low HDL.

## 7. Limitations & Caveats
- Waist circumference measurement technique varies between iliac crest and midpoint between lower rib and iliac crest.
- Does not measure visceral adipose volume directly (requires DEXA or MRI).
- Bioelectrical impedance body fat percentage is not collected in standard field screening.

## 8. Clinical Safety Notice
> **SAFETY NOTICE: Risk estimation is NOT diagnosis.**
> Anthropometric and metabolic risk scoring indicates lifestyle and vascular risk. It does not replace endocrine evaluation.
