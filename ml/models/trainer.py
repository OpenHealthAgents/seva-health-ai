"""Training interface for SevaHealth AI clinical risk models.

Orchestrates data preparation, feature engineering, preprocessing fitting,
model fitting, probability calibration, and registry registration.

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ml.features.feature_engineering import ClinicalFeatureEngineer
from ml.models.base import BaseRiskModel
from ml.models.classifiers import CalibratedRiskModel, EnsembleRiskModel, LogisticRiskModel
from ml.models.registry import ModelRegistry, ModelStage, RegisteredModelRecord
from ml.preprocessing.pipeline import ClinicalDataPreprocessor

logger = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    model: BaseRiskModel
    preprocessor: ClinicalDataPreprocessor
    feature_engineer: ClinicalFeatureEngineer
    train_metrics: Dict[str, float]
    val_metrics: Dict[str, float]
    model_version: str
    training_data_version: str
    feature_version: str
    evaluation_version: str


class ModelTrainer:
    """End-to-end training orchestrator for clinical risk models."""

    def __init__(
        self,
        model_version: str = "v1.0.0",
        training_data_version: str = "v1.0.0",
        feature_version: str = "v1.0.0",
        evaluation_version: str = "v1.0.0",
        registry: Optional[ModelRegistry] = None,
    ):
        self.model_version = model_version
        self.training_data_version = training_data_version
        self.feature_version = feature_version
        self.evaluation_version = evaluation_version
        self.registry = registry or ModelRegistry()

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        model_type: str = "calibrated_ensemble",  # "logistic", "ensemble", "calibrated_logistic", "calibrated_ensemble"
        target_col: str = "event_outcome",
        model_params: Optional[Dict[str, Any]] = None,
        imputation_strategy: str = "median",
        scaler_type: str = "standard",
    ) -> TrainingResult:
        """Trains clinical risk model end-to-end."""
        model_params = model_params or {}

        # 1. Feature Engineering
        feature_engineer = ClinicalFeatureEngineer(feature_version=self.feature_version)
        train_fe = feature_engineer.transform(train_df)
        val_fe = feature_engineer.transform(val_df)

        y_train = train_fe[target_col].values
        y_val = val_fe[target_col].values

        # Remove non-feature columns
        drop_cols = ["patient_id", target_col]
        train_clean = train_fe.drop(columns=[c for c in drop_cols if c in train_fe.columns])
        val_clean = val_fe.drop(columns=[c for c in drop_cols if c in val_fe.columns])

        # 2. Data Preprocessing
        preprocessor = ClinicalDataPreprocessor(
            preprocessing_version=self.feature_version,
            imputation_strategy=imputation_strategy,
            add_indicator_for_missing=True,
            clip_outliers=True,
            scaler_type=scaler_type,
        )

        X_train_proc = preprocessor.fit_transform(train_clean)
        X_val_proc = preprocessor.transform(val_clean)

        # 3. Model Instantiation
        if model_type == "logistic":
            model: BaseRiskModel = LogisticRiskModel(
                model_version=self.model_version,
                **model_params,
            )
        elif model_type == "ensemble":
            model = EnsembleRiskModel(
                model_version=self.model_version,
                **model_params,
            )
        elif model_type == "calibrated_logistic":
            base = LogisticRiskModel(model_version=self.model_version, **model_params)
            model = CalibratedRiskModel(
                base_model=base,
                method="sigmoid",
                cv=3,
                model_version=self.model_version,
            )
        elif model_type == "calibrated_ensemble":
            base = EnsembleRiskModel(model_version=self.model_version, **model_params)
            model = CalibratedRiskModel(
                base_model=base,
                method="isotonic",
                cv=3,
                model_version=self.model_version,
            )
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        # 4. Fitting
        model.fit(X_train_proc, y_train)

        # 5. Quick training/validation metric estimation
        from sklearn.metrics import brier_score_loss, roc_auc_score

        y_train_prob = model.predict_proba(X_train_proc)[:, 1]
        y_val_prob = model.predict_proba(X_val_proc)[:, 1]

        train_metrics = {
            "auroc": float(roc_auc_score(y_train, y_train_prob)),
            "brier_score": float(brier_score_loss(y_train, y_train_prob)),
        }
        val_metrics = {
            "auroc": float(roc_auc_score(y_val, y_val_prob)),
            "brier_score": float(brier_score_loss(y_val, y_val_prob)),
        }

        return TrainingResult(
            model=model,
            preprocessor=preprocessor,
            feature_engineer=feature_engineer,
            train_metrics=train_metrics,
            val_metrics=val_metrics,
            model_version=self.model_version,
            training_data_version=self.training_data_version,
            feature_version=self.feature_version,
            evaluation_version=self.evaluation_version,
        )

    def train_and_register(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        model_type: str = "calibrated_ensemble",
        target_col: str = "event_outcome",
        model_params: Optional[Dict[str, Any]] = None,
        stage: ModelStage = ModelStage.PRODUCTION,
        description: str = "",
    ) -> Tuple[TrainingResult, RegisteredModelRecord]:
        """Convenience method to train and immediately register the model bundle."""
        result = self.train(
            train_df=train_df,
            val_df=val_df,
            model_type=model_type,
            target_col=target_col,
            model_params=model_params,
        )

        record = self.registry.register_model(
            model=result.model,
            preprocessor=result.preprocessor,
            model_version=self.model_version,
            training_data_version=self.training_data_version,
            feature_version=self.feature_version,
            evaluation_version=self.evaluation_version,
            metrics=result.val_metrics,
            description=description,
            stage=stage,
        )

        return result, record
