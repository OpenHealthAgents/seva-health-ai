"""Synthetic demonstration dataset generator for NCD (cardiovascular and metabolic) risk.

Generates realistic demonstration cohorts with clinical vitals, lab biomarkers,
demographic attributes, and missingness patterns for ML experimentation.

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class DatasetMetadata:
    """Metadata for versioned datasets."""
    dataset_name: str
    data_version: str
    num_samples: int
    num_features: int
    positive_rate: float
    feature_names: List[str]
    demographic_groups: List[str]
    missing_rate_overall: float
    checksum: str
    created_at: str
    disclaimer: str = (
        "RESEARCH DEMONSTRATION ONLY: Synthetic dataset generated for ML experimentation. "
        "Contains simulated clinical values. Not clinically validated."
    )


class SyntheticCohortGenerator:
    """Generates synthetic patient cohorts with realistic distributions and correlations.

    Simulates:
    - Demographics: Age (18-85), Sex (Female/Male), Demographic Groups / Regions
    - Anthropometrics: Height, Weight, Calculated BMI
    - Vital Signs: Systolic BP, Diastolic BP, Resting Heart Rate
    - Laboratory Biomarkers: Fasting Blood Glucose, HbA1c, Total Cholesterol,
      HDL Cholesterol, LDL Cholesterol, Triglycerides, Serum Creatinine
    - Behavioral / History: Smoking status, Physical activity level, Family history of CVD/Diabetes
    - Clinical Outcome: 3-5 Year Cardiovascular/Metabolic Event (binary 0/1)
    """

    DEMOGRAPHIC_GROUPS = [
        "North-Rural",
        "North-Urban",
        "South-Rural",
        "South-Urban",
        "East-Rural",
        "East-Urban",
        "West-Rural",
        "West-Urban",
    ]

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.rng = np.random.RandomState(random_state)

    def generate(
        self,
        n_samples: int = 5000,
        missing_rate: float = 0.08,
        data_version: str = "v1.0.0",
    ) -> Tuple[pd.DataFrame, DatasetMetadata]:
        """Generate synthetic patient cohort dataframe and corresponding metadata."""
        n = n_samples
        rng = self.rng

        # 1. Demographics
        patient_ids = [f"SYN-PAT-{i+1:06d}" for i in range(n)]
        
        # Age distribution: multimodal mixture representing adult screening population
        age_comp = rng.choice([0, 1, 2], size=n, p=[0.40, 0.40, 0.20])
        age_raw = np.where(
            age_comp == 0,
            rng.normal(38, 9, n),
            np.where(age_comp == 1, rng.normal(56, 11, n), rng.normal(68, 8, n)),
        )
        age = np.clip(age_raw, 18, 85).round(1)

        sex = rng.choice(["Female", "Male"], size=n, p=[0.51, 0.49])
        demographic_group = rng.choice(self.DEMOGRAPHIC_GROUPS, size=n)

        # 2. Anthropometrics
        # Base height in cm and weight in kg correlated with sex and age
        height_cm = np.where(
            sex == "Male",
            rng.normal(168.0, 7.5, n),
            rng.normal(155.0, 6.5, n),
        ).round(1)
        
        # BMI baseline with realistic skew towards overweight in middle/older ages
        bmi_base = 23.5 + 0.06 * (age - 30) + rng.normal(0, 3.8, n)
        bmi = np.clip(bmi_base, 14.5, 48.0).round(1)
        weight_kg = (bmi * ((height_cm / 100.0) ** 2)).round(1)

        # 3. Behavioral Factors
        # Smoking higher in males in this cohort representation
        smoke_prob = np.where(sex == "Male", 0.28, 0.06)
        smoking_status = rng.binomial(1, smoke_prob, n)
        
        # Physical activity (0: Sedentary, 1: Moderate, 2: Active)
        activity_level = rng.choice([0, 1, 2], size=n, p=[0.45, 0.35, 0.20])
        
        # Family history of CVD or diabetes
        family_history = rng.binomial(1, 0.32, n)

        # 4. Vital Signs (correlated with Age, BMI, Smoking)
        # Systolic BP: normal ~ 120, increases with age and BMI
        sys_bp = (
            110.0
            + 0.55 * (age - 30)
            + 0.85 * (bmi - 23.0)
            + 6.0 * smoking_status
            + rng.normal(0, 12.0, n)
        )
        sys_bp = np.clip(sys_bp, 85.0, 220.0).round(1)

        # Diastolic BP: correlated with Systolic BP
        dia_bp = (
            68.0
            + 0.22 * (sys_bp - 110.0)
            + 0.30 * (bmi - 23.0)
            + rng.normal(0, 7.5, n)
        )
        dia_bp = np.clip(dia_bp, 50.0, 130.0).round(1)

        heart_rate = np.clip(
            72.0 + 0.25 * (bmi - 23.0) - 3.0 * activity_level + rng.normal(0, 8.5, n),
            45.0, 125.0
        ).round(1)

        # 5. Laboratory Biomarkers
        # Fasting Blood Glucose (mg/dL)
        fasting_glucose = (
            85.0
            + 0.40 * (age - 30)
            + 1.30 * (bmi - 23.0)
            + 12.0 * family_history
            + rng.normal(0, 18.0, n)
        )
        fasting_glucose = np.clip(fasting_glucose, 65.0, 320.0).round(1)

        # HbA1c (%) roughly correlated with glucose
        hba1c = (
            4.8
            + 0.02 * (fasting_glucose - 85.0)
            + 0.015 * (bmi - 23.0)
            + rng.normal(0, 0.45, n)
        )
        hba1c = np.clip(hba1c, 4.2, 13.5).round(2)

        # Lipid Panel (mg/dL)
        total_cholesterol = np.clip(
            170.0 + 0.65 * (age - 30) + 1.2 * (bmi - 23.0) + rng.normal(0, 28.0, n),
            100.0, 380.0
        ).round(1)

        hdl_cholesterol = np.where(
            sex == "Female",
            np.clip(52.0 - 0.45 * (bmi - 23.0) + 2.5 * activity_level + rng.normal(0, 7.5, n), 22.0, 95.0),
            np.clip(44.0 - 0.45 * (bmi - 23.0) + 2.5 * activity_level + rng.normal(0, 7.0, n), 20.0, 85.0),
        ).round(1)

        triglycerides = np.clip(
            120.0 + 0.8 * (age - 30) + 2.8 * (bmi - 23.0) + rng.normal(0, 42.0, n),
            45.0, 550.0
        ).round(1)

        # LDL estimated by Friedewald approximation + noise
        ldl_cholesterol = np.clip(
            total_cholesterol - hdl_cholesterol - (triglycerides / 5.0) + rng.normal(0, 10.0, n),
            40.0, 280.0
        ).round(1)

        # Serum Creatinine (mg/dL)
        creat_base = np.where(sex == "Male", 0.95, 0.78)
        serum_creatinine = np.clip(
            creat_base + 0.005 * (age - 30) + 0.002 * (sys_bp - 120.0) + rng.normal(0, 0.18, n),
            0.45, 4.2
        ).round(2)

        # 6. Clinical Ground Truth Outcome Simulation (Log-odds risk score)
        # Latent risk model calibrated to realistic 15-22% cardiovascular/cardiometabolic event rate
        log_odds = (
            -4.5
            + 0.048 * (age - 45)
            + 0.045 * (sys_bp - 125)
            + 0.035 * (bmi - 24)
            + 0.012 * (fasting_glucose - 95)
            + 0.35 * (hba1c - 5.6)
            + 0.008 * (ldl_cholesterol - 100)
            - 0.025 * (hdl_cholesterol - 45)
            + 0.65 * smoking_status
            + 0.45 * family_history
            - 0.30 * activity_level
            + (0.35 if "Rural" in "North-Rural" else 0.0)  # slight demographic heterogeneity
            + rng.normal(0, 0.6, n)
        )
        event_prob = 1.0 / (1.0 + np.exp(-log_odds))
        target_outcome = rng.binomial(1, event_prob, n)

        # Assemble DataFrame
        df = pd.DataFrame({
            "patient_id": patient_ids,
            "age": age,
            "sex": sex,
            "demographic_group": demographic_group,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "bmi": bmi,
            "smoking_status": smoking_status,
            "physical_activity": activity_level,
            "family_history": family_history,
            "systolic_bp": sys_bp,
            "diastolic_bp": dia_bp,
            "heart_rate": heart_rate,
            "fasting_glucose": fasting_glucose,
            "hba1c": hba1c,
            "total_cholesterol": total_cholesterol,
            "hdl_cholesterol": hdl_cholesterol,
            "ldl_cholesterol": ldl_cholesterol,
            "triglycerides": triglycerides,
            "serum_creatinine": serum_creatinine,
            "event_outcome": target_outcome,
        })

        # 7. Introduce realistic missingness (MCAR & MAR in lab features)
        if missing_rate > 0.0:
            lab_cols = [
                "hba1c",
                "fasting_glucose",
                "total_cholesterol",
                "hdl_cholesterol",
                "ldl_cholesterol",
                "triglycerides",
                "serum_creatinine",
                "heart_rate",
            ]
            for col in lab_cols:
                # Slightly higher missingness in rural cohorts
                col_missing_prob = np.where(
                    df["demographic_group"].str.contains("Rural"),
                    missing_rate * 1.4,
                    missing_rate * 0.7,
                )
                mask = rng.rand(n) < col_missing_prob
                df.loc[mask, col] = np.nan

        # Calculate overall missingness rate and checksum
        overall_missing = float(df.isna().sum().sum() / (df.shape[0] * df.shape[1]))
        data_bytes = df.to_csv(index=False).encode("utf-8")
        checksum = hashlib.sha256(data_bytes).hexdigest()

        metadata = DatasetMetadata(
            dataset_name="synthetic_ncd_cardiovascular_cohort",
            data_version=data_version,
            num_samples=n,
            num_features=len(df.columns) - 2,  # exclude patient_id and event_outcome
            positive_rate=float(df["event_outcome"].mean()),
            feature_names=[c for c in df.columns if c not in ["patient_id", "event_outcome"]],
            demographic_groups=list(df["demographic_group"].unique()),
            missing_rate_overall=round(overall_missing, 4),
            checksum=checksum,
            created_at=pd.Timestamp.now().isoformat(),
        )

        return df, metadata
