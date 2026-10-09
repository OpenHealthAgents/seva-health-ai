"""SevaHealth AI - ML Experimentation Framework.

High-performance, reproducible machine learning framework for preventive health risk stratification.
Includes synthetic data generators, preprocessing pipelines, clinical feature engineering,
model registry, comprehensive evaluation (discrimination, calibration, demographic fairness,
missingness stress tests), real-time inference, and model cards.

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from ml.datasets.dataset_loader import DatasetLoader
from ml.datasets.synthetic_generator import DatasetMetadata, SyntheticCohortGenerator
from ml.evaluation.demographics import DemographicEvaluationReport, DemographicEvaluator
from ml.evaluation.evaluator import CompleteEvaluationReport, ModelEvaluator
from ml.evaluation.metrics import (
    CalibrationMetrics,
    ClinicalEvaluationMetrics,
    ClinicalMetricsCalculator,
    ConfusionMatrixValues,
)
from ml.evaluation.missingness import (
    MissingDataSensitivityAnalyzer,
    MissingDataSensitivityReport,
)
from ml.features.feature_engineering import ClinicalFeatureEngineer, FeatureSetMetadata
from ml.inference.engine import PatientRiskAssessment, RiskInferenceEngine
from ml.model_cards.generator import ModelCardData, ModelCardGenerator
from ml.models.base import BaseRiskModel
from ml.models.classifiers import (
    CalibratedRiskModel,
    EnsembleRiskModel,
    LogisticRiskModel,
)
from ml.models.registry import ModelRegistry, ModelStage, RegisteredModelRecord
from ml.models.trainer import ModelTrainer, TrainingResult
from ml.preprocessing.pipeline import PHYSIOLOGICAL_BOUNDS, ClinicalDataPreprocessor

__version__ = "0.1.0"

__all__ = [
    # Datasets
    "SyntheticCohortGenerator",
    "DatasetMetadata",
    "DatasetLoader",
    # Preprocessing
    "PHYSIOLOGICAL_BOUNDS",
    "ClinicalDataPreprocessor",
    # Features
    "ClinicalFeatureEngineer",
    "FeatureSetMetadata",
    # Models & Registry
    "BaseRiskModel",
    "LogisticRiskModel",
    "EnsembleRiskModel",
    "CalibratedRiskModel",
    "ModelRegistry",
    "ModelStage",
    "RegisteredModelRecord",
    "ModelTrainer",
    "TrainingResult",
    # Evaluation
    "ClinicalMetricsCalculator",
    "ClinicalEvaluationMetrics",
    "CalibrationMetrics",
    "ConfusionMatrixValues",
    "DemographicEvaluator",
    "DemographicEvaluationReport",
    "MissingDataSensitivityAnalyzer",
    "MissingDataSensitivityReport",
    "ModelEvaluator",
    "CompleteEvaluationReport",
    # Inference
    "RiskInferenceEngine",
    "PatientRiskAssessment",
    # Model Cards
    "ModelCardGenerator",
    "ModelCardData",
]
