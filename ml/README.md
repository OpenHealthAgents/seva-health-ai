# SevaHealth AI Machine Learning & Feature Engineering Pipeline

This directory contains the feature transformations, clinical guidelines mathematical scoring models, and synthetic evaluation datasets for NCD risk stratification:

```
ml/
├── datasets/             # Synthetic demographic & clinical observation baseline generators
├── feature-engineering/  # Anthropometric transformations (BMI, Waist-to-Height ratio, FIB-4)
├── models/               # Multi-domain guideline scoring models (ICMR IDRS, AHA/ACC, WHO-SEAR)
├── evaluation/           # Model calibration, discrimination (ROC-AUC), and clinical sensitivity metrics
└── inference/            # Sub-second inference pipeline with SHAP-style feature attribution waterfalls
```
