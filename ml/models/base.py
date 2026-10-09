"""Abstract base class for clinical risk models."""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd


class BaseRiskModel(abc.ABC):
    """Abstract base class for all risk prediction models in SevaHealth AI."""

    def __init__(self, model_name: str, model_version: str):
        self.model_name = model_name
        self.model_version = model_version
        self.is_fitted: bool = False
        self.feature_names_: List[str] = []

    @abc.abstractmethod
    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]) -> BaseRiskModel:
        """Fit model on training feature matrix and ground-truth targets."""
        pass

    @abc.abstractmethod
    def predict(self, X: Union[pd.DataFrame, np.ndarray], threshold: float = 0.5) -> np.ndarray:
        """Predict binary risk classification."""
        pass

    @abc.abstractmethod
    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predict continuous probability of event [P(y=0), P(y=1)]."""
        pass

    @abc.abstractmethod
    def get_feature_importances(self) -> Dict[str, float]:
        """Return feature importance or normalized coefficient dictionary."""
        pass

    @abc.abstractmethod
    def save(self, filepath: Union[str, Path]) -> None:
        """Persist model artifact."""
        pass

    @classmethod
    @abc.abstractmethod
    def load(cls, filepath: Union[str, Path]) -> BaseRiskModel:
        """Load model artifact from disk."""
        pass

    def get_params(self) -> Dict[str, Any]:
        """Return model hyperparameters."""
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "is_fitted": self.is_fitted,
        }
