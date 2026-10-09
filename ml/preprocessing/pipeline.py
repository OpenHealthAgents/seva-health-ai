"""Clinical data preprocessing pipeline with robust imputation, outlier clipping, and scaling.

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import json
import os
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, RobustScaler, StandardScaler


# Clinically reasonable physiological boundaries for plausibility clipping
PHYSIOLOGICAL_BOUNDS: Dict[str, Tuple[float, float]] = {
    "age": (18.0, 110.0),
    "height_cm": (100.0, 230.0),
    "weight_kg": (25.0, 250.0),
    "bmi": (12.0, 65.0),
    "systolic_bp": (70.0, 260.0),
    "diastolic_bp": (40.0, 150.0),
    "heart_rate": (40.0, 200.0),
    "fasting_glucose": (40.0, 600.0),
    "hba1c": (3.5, 18.0),
    "total_cholesterol": (80.0, 500.0),
    "hdl_cholesterol": (10.0, 140.0),
    "ldl_cholesterol": (20.0, 400.0),
    "triglycerides": (30.0, 1200.0),
    "serum_creatinine": (0.2, 15.0),
}


class ClinicalDataPreprocessor:
    """End-to-end clinical data preprocessor with schema persistence and versioning."""

    def __init__(
        self,
        preprocessing_version: str = "v1.0.0",
        imputation_strategy: str = "median",
        add_indicator_for_missing: bool = True,
        clip_outliers: bool = True,
        scaler_type: str = "standard",  # "standard", "robust", or "none"
    ):
        self.preprocessing_version = preprocessing_version
        self.imputation_strategy = imputation_strategy
        self.add_indicator_for_missing = add_indicator_for_missing
        self.clip_outliers = clip_outliers
        self.scaler_type = scaler_type

        # Fitted parameters
        self.numerical_impute_values_: Dict[str, float] = {}
        self.categorical_impute_values_: Dict[str, str] = {}
        self.numerical_cols_: List[str] = []
        self.categorical_cols_: List[str] = []
        self.one_hot_encoder_: Optional[OneHotEncoder] = None
        self.scaler_: Optional[Union[StandardScaler, RobustScaler]] = None
        self.feature_names_out_: List[str] = []
        self.is_fitted: bool = False

    def fit(
        self,
        df: pd.DataFrame,
        numerical_cols: Optional[List[str]] = None,
        categorical_cols: Optional[List[str]] = None,
    ) -> ClinicalDataPreprocessor:
        """Fit preprocessor parameters on training cohort."""
        df_copy = df.copy()

        # Identify numerical and categorical columns if not provided
        if numerical_cols is None or categorical_cols is None:
            detected_num = []
            detected_cat = []
            for col in df_copy.columns:
                if col in ["patient_id", "event_outcome"]:
                    continue
                if pd.api.types.is_numeric_dtype(df_copy[col]):
                    detected_num.append(col)
                else:
                    detected_cat.append(col)
            self.numerical_cols_ = numerical_cols or detected_num
            self.categorical_cols_ = categorical_cols or detected_cat
        else:
            self.numerical_cols_ = numerical_cols
            self.categorical_cols_ = categorical_cols

        # 1. Compute imputation values
        for col in self.numerical_cols_:
            if col in df_copy.columns:
                vals = df_copy[col].dropna()
                if self.imputation_strategy == "median":
                    self.numerical_impute_values_[col] = float(vals.median()) if len(vals) > 0 else 0.0
                else:
                    self.numerical_impute_values_[col] = float(vals.mean()) if len(vals) > 0 else 0.0

        for col in self.categorical_cols_:
            if col in df_copy.columns:
                mode_series = df_copy[col].dropna().mode()
                self.categorical_impute_values_[col] = (
                    str(mode_series.iloc[0]) if len(mode_series) > 0 else "Unknown"
                )

        # 2. Impute and clip training data for scaler/encoder fit
        processed_df = self._impute_and_clip(df_copy)

        # 3. Fit OneHotEncoder on categorical columns
        if self.categorical_cols_:
            self.one_hot_encoder_ = OneHotEncoder(
                sparse_output=False,
                handle_unknown="ignore",
            )
            self.one_hot_encoder_.fit(processed_df[self.categorical_cols_])

        # 4. Prepare feature names
        num_features = list(self.numerical_cols_)
        if self.add_indicator_for_missing:
            # Add indicator columns for features that could be missing
            num_features.extend([f"{col}_is_missing" for col in self.numerical_cols_])

        cat_features = []
        if self.one_hot_encoder_ and self.categorical_cols_:
            cat_features = list(self.one_hot_encoder_.get_feature_names_out(self.categorical_cols_))

        all_features = num_features + cat_features
        self.feature_names_out_ = all_features

        # 5. Fit Scaler on numerical features (excluding binary indicators)
        if self.scaler_type == "standard":
            self.scaler_ = StandardScaler()
            self.scaler_.fit(processed_df[self.numerical_cols_])
        elif self.scaler_type == "robust":
            self.scaler_ = RobustScaler()
            self.scaler_.fit(processed_df[self.numerical_cols_])
        else:
            self.scaler_ = None

        self.is_fitted = True
        return self

    def _impute_and_clip(self, df: pd.DataFrame) -> pd.DataFrame:
        """Internal helper to apply physiological clipping and imputation."""
        out_df = df.copy()

        # Outlier bounds clipping
        if self.clip_outliers:
            for col, (lower, upper) in PHYSIOLOGICAL_BOUNDS.items():
                if col in out_df.columns and col in self.numerical_cols_:
                    out_df[col] = out_df[col].clip(lower=lower, upper=upper)

        # Impute numericals
        for col in self.numerical_cols_:
            fill_val = self.numerical_impute_values_.get(col, 0.0)
            if col in out_df.columns:
                out_df[col] = out_df[col].fillna(fill_val)
            else:
                out_df[col] = fill_val

        # Impute categoricals
        for col in self.categorical_cols_:
            fill_val = self.categorical_impute_values_.get(col, "Unknown")
            if col in out_df.columns:
                out_df[col] = out_df[col].fillna(fill_val).astype(str)
            else:
                out_df[col] = fill_val

        return out_df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform incoming raw dataframe into standardized feature matrix."""
        if not self.is_fitted:
            raise RuntimeError("Preprocessor must be fitted before calling transform.")

        df_copy = df.copy()

        # Compute missing indicators before imputation
        missing_indicators = {}
        if self.add_indicator_for_missing:
            for col in self.numerical_cols_:
                if col in df_copy.columns:
                    missing_indicators[f"{col}_is_missing"] = df_copy[col].isna().astype(float)
                else:
                    missing_indicators[f"{col}_is_missing"] = np.ones(len(df_copy), dtype=float)

        # Apply clipping and imputation
        processed_df = self._impute_and_clip(df_copy)

        # Transform numericals with scaler
        if self.scaler_ is not None:
            num_scaled = self.scaler_.transform(processed_df[self.numerical_cols_])
        else:
            num_scaled = processed_df[self.numerical_cols_].values

        num_scaled_df = pd.DataFrame(
            num_scaled,
            columns=self.numerical_cols_,
            index=df_copy.index,
        )

        parts = [num_scaled_df]

        if self.add_indicator_for_missing:
            ind_df = pd.DataFrame(missing_indicators, index=df_copy.index)
            parts.append(ind_df)

        if self.categorical_cols_ and self.one_hot_encoder_ is not None:
            cat_data = processed_df[self.categorical_cols_]
            cat_encoded = self.one_hot_encoder_.transform(cat_data)
            cat_df = pd.DataFrame(
                cat_encoded,
                columns=self.one_hot_encoder_.get_feature_names_out(self.categorical_cols_),
                index=df_copy.index,
            )
            parts.append(cat_df)

        transformed_df = pd.concat(parts, axis=1)
        # Ensure column alignment with feature_names_out_
        for missing_col in self.feature_names_out_:
            if missing_col not in transformed_df.columns:
                transformed_df[missing_col] = 0.0

        return transformed_df[self.feature_names_out_]

    def fit_transform(
        self,
        df: pd.DataFrame,
        numerical_cols: Optional[List[str]] = None,
        categorical_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Fit and transform convenience method."""
        return self.fit(df, numerical_cols, categorical_cols).transform(df)

    def save(self, filepath: Union[str, Path]) -> None:
        """Persist preprocessor to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> ClinicalDataPreprocessor:
        """Load persisted preprocessor from disk."""
        with open(filepath, "rb") as f:
            return pickle.load(f)
