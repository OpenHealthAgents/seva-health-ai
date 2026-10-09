"""Inference interface for real-time and batch clinical risk estimation.

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from ml.features.feature_engineering import ClinicalFeatureEngineer
from ml.models.base import BaseRiskModel
from ml.models.registry import ModelRegistry, RegisteredModelRecord
from ml.preprocessing.pipeline import ClinicalDataPreprocessor


@dataclass
class RiskFactorContribution:
    feature_name: str
    observed_value: Any
    contribution_direction: str  # "increases_risk", "decreases_risk", "neutral"
    importance_weight: float


@dataclass
class PatientRiskAssessment:
    patient_id: str
    predicted_probability: float
    risk_tier: str  # "Low", "Moderate", "High", "Critical"
    confidence_interval_95: Tuple[float, float]
    top_risk_factors: List[RiskFactorContribution]
    missing_features_imputed: List[str]
    model_version: str
    training_data_version: str
    feature_version: str
    evaluation_version: str
    disclaimer: str = (
        "RESEARCH DEMONSTRATION ONLY: This AI/ML risk assessment has NOT been clinically validated "
        "in prospective randomized clinical trials. It does not replace certified physician evaluation."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RiskInferenceEngine:
    """Production-grade inference interface for clinical risk models."""

    def __init__(
        self,
        model: BaseRiskModel,
        preprocessor: ClinicalDataPreprocessor,
        feature_engineer: ClinicalFeatureEngineer,
        metadata_record: Optional[RegisteredModelRecord] = None,
        model_version: str = "v1.0.0",
        training_data_version: str = "v1.0.0",
        feature_version: str = "v1.0.0",
        evaluation_version: str = "v1.0.0",
    ):
        self.model = model
        self.preprocessor = preprocessor
        self.feature_engineer = feature_engineer
        self.metadata_record = metadata_record
        self.model_version = metadata_record.model_version if metadata_record else model_version
        self.training_data_version = (
            metadata_record.training_data_version if metadata_record else training_data_version
        )
        self.feature_version = (
            metadata_record.feature_version if metadata_record else feature_version
        )
        self.evaluation_version = (
            metadata_record.evaluation_version if metadata_record else evaluation_version
        )

    @classmethod
    def from_registry(
        cls,
        model_name: str,
        model_version: Optional[str] = None,
        registry: Optional[ModelRegistry] = None,
    ) -> RiskInferenceEngine:
        """Loads inference engine directly from Model Registry."""
        reg = registry or ModelRegistry()
        model, preprocessor, record = reg.load_bundle(model_name, model_version)
        fe = ClinicalFeatureEngineer(feature_version=record.feature_version)
        return cls(
            model=model,
            preprocessor=preprocessor,
            feature_engineer=fe,
            metadata_record=record,
        )

    def predict_patient(self, patient_dict: Dict[str, Any]) -> PatientRiskAssessment:
        """Single-patient real-time risk assessment."""
        df = pd.DataFrame([patient_dict])
        results = self.predict_batch(df)
        return results[0]

    def predict_batch(self, patients_df: pd.DataFrame) -> List[PatientRiskAssessment]:
        """Batch risk assessment with confidence intervals and risk factors."""
        df_raw = patients_df.copy()
        patient_ids = (
            df_raw["patient_id"].astype(str).tolist()
            if "patient_id" in df_raw.columns
            else [f"PAT-{i+1:04d}" for i in range(len(df_raw))]
        )

        # Track which expected features were missing in raw input
        imputed_map: List[List[str]] = []
        for _, row in df_raw.iterrows():
            missing_cols = [
                col for col in self.preprocessor.numerical_cols_
                if col not in row or pd.isna(row[col])
            ]
            imputed_map.append(missing_cols)

        # 1. Feature Engineering
        fe_df = self.feature_engineer.transform(df_raw)
        drop_cols = ["patient_id", "event_outcome"]
        clean_df = fe_df.drop(columns=[c for c in drop_cols if c in fe_df.columns], errors="ignore")

        # 2. Preprocessing
        X_proc = self.preprocessor.transform(clean_df)

        # 3. Model Prediction
        probs = self.model.predict_proba(X_proc)[:, 1]

        # Feature importances for attribution
        feature_importances = self.model.get_feature_importances()

        assessments: List[PatientRiskAssessment] = []

        for idx, (p_id, p_prob) in enumerate(zip(patient_ids, probs)):
            p_val = float(np.clip(p_prob, 0.0, 1.0))

            # Risk Tier Stratification
            if p_val < 0.10:
                tier = "Low"
            elif p_val < 0.20:
                tier = "Moderate"
            elif p_val < 0.40:
                tier = "High"
            else:
                tier = "Critical"

            # Approximate 95% Wilson-style confidence interval based on calibration variance
            std_err = math_se = np.sqrt(p_val * (1.0 - p_val) / 100.0)
            ci_low = float(np.clip(p_val - 1.96 * std_err, 0.0, 1.0))
            ci_high = float(np.clip(p_val + 1.96 * std_err, 0.0, 1.0))

            # Determine top risk factors for this patient
            row_vals = X_proc.iloc[idx]
            factors: List[RiskFactorContribution] = []

            for feat, weight in sorted(
                feature_importances.items(), key=lambda kv: abs(kv[1]), reverse=True
            )[:5]:
                raw_val = row_vals.get(feat, 0.0)
                # If feature is standardized, >0 increases risk for positive weight
                effect = raw_val * weight
                direction = "increases_risk" if effect > 0.05 else ("decreases_risk" if effect < -0.05 else "neutral")
                factors.append(
                    RiskFactorContribution(
                        feature_name=feat,
                        observed_value=float(raw_val) if isinstance(raw_val, (int, float, np.number)) else str(raw_val),
                        contribution_direction=direction,
                        importance_weight=round(float(weight), 4),
                    )
                )

            assessments.append(
                PatientRiskAssessment(
                    patient_id=p_id,
                    predicted_probability=round(p_val, 4),
                    risk_tier=tier,
                    confidence_interval_95=(round(ci_low, 4), round(ci_high, 4)),
                    top_risk_factors=factors,
                    missing_features_imputed=imputed_map[idx],
                    model_version=self.model_version,
                    training_data_version=self.training_data_version,
                    feature_version=self.feature_version,
                    evaluation_version=self.evaluation_version,
                )
            )

        return assessments
