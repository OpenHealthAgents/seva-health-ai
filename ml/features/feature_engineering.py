"""Clinical feature engineering for cardiometabolic risk stratification.

Derives physiological indices, cardiovascular risk ratios, and metabolic syndrome flags.

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class FeatureSetMetadata:
    """Metadata describing the feature set version."""
    feature_version: str
    base_features: List[str]
    derived_features: List[str]
    all_features: List[str]
    description: str


class ClinicalFeatureEngineer:
    """Transforms raw clinical and demographic data into engineered risk features."""

    def __init__(self, feature_version: str = "v1.0.0"):
        self.feature_version = feature_version
        self.derived_feature_names: List[str] = [
            "mean_arterial_pressure",
            "pulse_pressure",
            "cholesterol_hdl_ratio",
            "triglyceride_hdl_ratio",
            "hypertension_stage",
            "glycemic_risk_flag",
            "metabolic_syndrome_score",
            "cvd_age_bp_interaction",
            "lifestyle_risk_index",
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derives clinical features from input dataframe."""
        out = df.copy()

        # 1. Hemodynamic features
        # Mean Arterial Pressure (MAP) = (2 * DBP + SBP) / 3
        if "systolic_bp" in out.columns and "diastolic_bp" in out.columns:
            out["mean_arterial_pressure"] = (
                2.0 * out["diastolic_bp"] + out["systolic_bp"]
            ) / 3.0
            out["pulse_pressure"] = out["systolic_bp"] - out["diastolic_bp"]
        else:
            out["mean_arterial_pressure"] = np.nan
            out["pulse_pressure"] = np.nan

        # 2. Lipid atherogenic ratios
        if "total_cholesterol" in out.columns and "hdl_cholesterol" in out.columns:
            hdl_safe = out["hdl_cholesterol"].replace(0, np.nan)
            out["cholesterol_hdl_ratio"] = out["total_cholesterol"] / hdl_safe
        else:
            out["cholesterol_hdl_ratio"] = np.nan

        if "triglycerides" in out.columns and "hdl_cholesterol" in out.columns:
            hdl_safe = out["hdl_cholesterol"].replace(0, np.nan)
            out["triglyceride_hdl_ratio"] = out["triglycerides"] / hdl_safe
        else:
            out["triglyceride_hdl_ratio"] = np.nan

        # 3. Hypertension Stage (AHA/ACC 2017 classification)
        # 0: Normal (<120 and <80)
        # 1: Elevated (120-129 and <80)
        # 2: Stage 1 (130-139 or 80-89)
        # 3: Stage 2 (>=140 or >=90)
        if "systolic_bp" in out.columns and "diastolic_bp" in out.columns:
            sbp = out["systolic_bp"]
            dbp = out["diastolic_bp"]
            htn_stage = np.zeros(len(out), dtype=float)
            htn_stage[(sbp >= 120) & (sbp < 130) & (dbp < 80)] = 1.0
            htn_stage[((sbp >= 130) & (sbp < 140)) | ((dbp >= 80) & (dbp < 90))] = 2.0
            htn_stage[(sbp >= 140) | (dbp >= 90)] = 3.0
            out["hypertension_stage"] = htn_stage
        else:
            out["hypertension_stage"] = np.nan

        # 4. Glycemic Risk Flag (0: Normal, 1: Impaired/Prediabetes, 2: Diabetic Range)
        if "fasting_glucose" in out.columns or "hba1c" in out.columns:
            fg = out["fasting_glucose"] if "fasting_glucose" in out.columns else pd.Series(np.nan, index=out.index)
            a1c = out["hba1c"] if "hba1c" in out.columns else pd.Series(np.nan, index=out.index)
            glyc_flag = np.zeros(len(out), dtype=float)
            # Prediabetes: glucose 100-125 or HbA1c 5.7-6.4
            prediab = ((fg >= 100) & (fg < 126)) | ((a1c >= 5.7) & (a1c < 6.5))
            # Diabetes: glucose >=126 or HbA1c >=6.5
            diab = (fg >= 126) | (a1c >= 6.5)
            glyc_flag[prediab] = 1.0
            glyc_flag[diab] = 2.0
            out["glycemic_risk_flag"] = glyc_flag
        else:
            out["glycemic_risk_flag"] = np.nan

        # 5. Metabolic Syndrome Component Score (0 to 5)
        # Criteria: SBP>=130 or DBP>=85; Glucose>=100; Triglycerides>=150; Low HDL (<40M/<50F); BMI>=23 (Asian cutoff)
        met_score = pd.Series(0.0, index=out.index)
        if "systolic_bp" in out.columns and "diastolic_bp" in out.columns:
            met_score += ((out["systolic_bp"] >= 130) | (out["diastolic_bp"] >= 85)).astype(float)
        if "fasting_glucose" in out.columns:
            met_score += (out["fasting_glucose"] >= 100).fillna(0).astype(float)
        if "triglycerides" in out.columns:
            met_score += (out["triglycerides"] >= 150).fillna(0).astype(float)
        if "hdl_cholesterol" in out.columns and "sex" in out.columns:
            low_hdl = ((out["sex"] == "Male") & (out["hdl_cholesterol"] < 40)) | (
                (out["sex"] == "Female") & (out["hdl_cholesterol"] < 50)
            )
            met_score += low_hdl.fillna(0).astype(float)
        if "bmi" in out.columns:
            met_score += (out["bmi"] >= 23.0).fillna(0).astype(float)
        out["metabolic_syndrome_score"] = met_score

        # 6. Interaction term: Age x Systolic BP / 100
        if "age" in out.columns and "systolic_bp" in out.columns:
            out["cvd_age_bp_interaction"] = (out["age"] * out["systolic_bp"]) / 100.0
        else:
            out["cvd_age_bp_interaction"] = np.nan

        # 7. Lifestyle Risk Index (Smoking + Physical Inactivity)
        lifestyle = pd.Series(0.0, index=out.index)
        if "smoking_status" in out.columns:
            lifestyle += out["smoking_status"].fillna(0).astype(float) * 2.0
        if "physical_activity" in out.columns:
            # 0 is sedentary (highest risk), 2 is active
            lifestyle += (2.0 - out["physical_activity"].fillna(1)).astype(float)
        out["lifestyle_risk_index"] = lifestyle

        return out

    def get_metadata(self, base_features: List[str]) -> FeatureSetMetadata:
        """Returns metadata for the engineered feature set."""
        all_feats = base_features + self.derived_feature_names
        return FeatureSetMetadata(
            feature_version=self.feature_version,
            base_features=base_features,
            derived_features=self.derived_feature_names,
            all_features=all_feats,
            description="Clinical hemodynamic, lipid atherogenic, and metabolic syndrome indices.",
        )
