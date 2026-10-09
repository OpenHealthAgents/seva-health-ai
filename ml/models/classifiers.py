"""Clinical risk model implementations: Logistic Regression, Gradient Boosting, and Calibrated Wrapper.

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from ml.models.base import BaseRiskModel


class LogisticRiskModel(BaseRiskModel):
    """Interpretable penalized logistic regression model with odds ratio support."""

    def __init__(
        self,
        model_version: str = "v1.0.0",
        C: float = 1.0,
        solver: str = "lbfgs",
        random_state: int = 42,
    ):
        super().__init__(model_name="logistic_risk_model", model_version=model_version)
        self.C = C
        self.solver = solver
        self.random_state = random_state
        self.estimator_ = LogisticRegression(
            C=self.C,
            solver=self.solver,
            random_state=self.random_state,
            max_iter=1000,
        )

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]) -> LogisticRiskModel:
        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
            X_arr = X.values
        else:
            self.feature_names_ = [f"f_{i}" for i in range(X.shape[1])]
            X_arr = X

        y_arr = y.values if isinstance(y, pd.Series) else y
        self.estimator_.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray], threshold: float = 0.5) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= threshold).astype(int)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        X_arr = X.values if isinstance(X, pd.DataFrame) else X
        return self.estimator_.predict_proba(X_arr)

    def get_feature_importances(self) -> Dict[str, float]:
        if not self.is_fitted:
            return {}
        coefs = self.estimator_.coef_[0]
        # Return absolute weight ranking
        return {
            feat: float(coef)
            for feat, coef in zip(self.feature_names_, coefs)
        }

    def get_odds_ratios(self) -> Dict[str, float]:
        """Compute odds ratios exp(beta) for clinical interpretability."""
        if not self.is_fitted:
            return {}
        coefs = self.estimator_.coef_[0]
        return {
            feat: float(np.exp(coef))
            for feat, coef in zip(self.feature_names_, coefs)
        }

    def save(self, filepath: Union[str, Path]) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> LogisticRiskModel:
        with open(filepath, "rb") as f:
            return pickle.load(f)


class EnsembleRiskModel(BaseRiskModel):
    """Gradient Boosting ensemble classifier for non-linear risk interactions."""

    def __init__(
        self,
        model_version: str = "v1.0.0",
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 3,
        random_state: int = 42,
    ):
        super().__init__(model_name="gradient_boosting_risk_model", model_version=model_version)
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.random_state = random_state
        self.estimator_ = GradientBoostingClassifier(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            random_state=self.random_state,
        )

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]) -> EnsembleRiskModel:
        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
            X_arr = X.values
        else:
            self.feature_names_ = [f"f_{i}" for i in range(X.shape[1])]
            X_arr = X

        y_arr = y.values if isinstance(y, pd.Series) else y
        self.estimator_.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray], threshold: float = 0.5) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= threshold).astype(int)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        X_arr = X.values if isinstance(X, pd.DataFrame) else X
        return self.estimator_.predict_proba(X_arr)

    def get_feature_importances(self) -> Dict[str, float]:
        if not self.is_fitted:
            return {}
        importances = self.estimator_.feature_importances_
        return {
            feat: float(imp)
            for feat, imp in zip(self.feature_names_, importances)
        }

    def save(self, filepath: Union[str, Path]) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> EnsembleRiskModel:
        with open(filepath, "rb") as f:
            return pickle.load(f)


class CalibratedRiskModel(BaseRiskModel):
    """Wrapper that applies Isotonic or Sigmoid (Platt) probability calibration.
    
    Calibration is essential in clinical risk prediction so that a predicted probability
    of 0.20 corresponds to an empirical 20% event rate in that patient group.
    """

    def __init__(
        self,
        base_model: BaseRiskModel,
        method: str = "sigmoid",  # "sigmoid" (Platt) or "isotonic"
        cv: Union[int, str] = 3,
        model_version: str = "v1.0.0",
    ):
        super().__init__(
            model_name=f"calibrated_{base_model.model_name}",
            model_version=model_version,
        )
        self.base_model = base_model
        self.method = method
        self.cv = cv
        self.calibrated_classifier_: Optional[CalibratedClassifierCV] = None

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]) -> CalibratedRiskModel:
        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
            X_arr = X.values
        else:
            self.feature_names_ = [f"f_{i}" for i in range(X.shape[1])]
            X_arr = X

        y_arr = y.values if isinstance(y, pd.Series) else y

        # Fit base model so feature importances and coefficients are computed
        self.base_model.fit(X, y)
        self.feature_names_ = getattr(self.base_model, "feature_names_", list(self.feature_names_))

        # Wrap underlying estimator
        base_estimator = getattr(self.base_model, "estimator_", None)
        if base_estimator is None:
            raise ValueError("base_model must have an estimator_ attribute for calibration.")

        self.calibrated_classifier_ = CalibratedClassifierCV(
            estimator=base_estimator,
            method=self.method,
            cv=self.cv,
        )
        self.calibrated_classifier_.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray], threshold: float = 0.5) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= threshold).astype(int)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        if not self.is_fitted or self.calibrated_classifier_ is None:
            raise RuntimeError("Calibrated model is not fitted.")
        X_arr = X.values if isinstance(X, pd.DataFrame) else X
        return self.calibrated_classifier_.predict_proba(X_arr)

    def get_feature_importances(self) -> Dict[str, float]:
        # Return base model feature importances if available
        if hasattr(self.base_model, "get_feature_importances"):
            return self.base_model.get_feature_importances()
        return {}

    def get_odds_ratios(self) -> Dict[str, float]:
        """Compute odds ratios exp(beta) from underlying model if available."""
        if hasattr(self.base_model, "get_odds_ratios"):
            return self.base_model.get_odds_ratios()
        return {}

    def save(self, filepath: Union[str, Path]) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> CalibratedRiskModel:
        with open(filepath, "rb") as f:
            return pickle.load(f)
