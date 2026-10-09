"""Dataset loader, splitting, schema validation, and version tracking."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ml.datasets.synthetic_generator import DatasetMetadata, SyntheticCohortGenerator


class DatasetLoader:
    """Manages loading, splitting, and versioning of datasets."""

    def __init__(self, data_dir: str = "ml/datasets/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_or_generate_synthetic(
        self,
        n_samples: int = 5000,
        missing_rate: float = 0.08,
        version: str = "v1.0.0",
        force_regenerate: bool = False,
    ) -> Tuple[pd.DataFrame, DatasetMetadata]:
        """Loads existing synthetic dataset if version matches or generates a fresh one."""
        csv_path = self.data_dir / f"cohort_{version}.csv"
        meta_path = self.data_dir / f"cohort_{version}_metadata.json"

        if csv_path.exists() and meta_path.exists() and not force_regenerate:
            df = pd.read_csv(csv_path)
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_dict = json.load(f)
            metadata = DatasetMetadata(**meta_dict)
            return df, metadata

        # Generate fresh
        generator = SyntheticCohortGenerator(random_state=42)
        df, metadata = generator.generate(
            n_samples=n_samples,
            missing_rate=missing_rate,
            data_version=version,
        )

        # Save to disk
        df.to_csv(csv_path, index=False)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, indent=2)

        return df, metadata

    def get_train_val_test_splits(
        self,
        df: pd.DataFrame,
        target_col: str = "event_outcome",
        test_size: float = 0.20,
        val_size: float = 0.15,
        random_state: int = 42,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Performs stratified train/val/test splits."""
        strat_col = df[target_col]
        # First split into train_val and test
        df_train_val, df_test = train_test_split(
            df,
            test_size=test_size,
            stratify=strat_col,
            random_state=random_state,
        )

        # Then split train_val into train and val
        relative_val_size = val_size / (1.0 - test_size)
        df_train, df_val = train_test_split(
            df_train_val,
            test_size=relative_val_size,
            stratify=df_train_val[target_col],
            random_state=random_state,
        )

        return (
            df_train.reset_index(drop=True),
            df_val.reset_index(drop=True),
            df_test.reset_index(drop=True),
        )
