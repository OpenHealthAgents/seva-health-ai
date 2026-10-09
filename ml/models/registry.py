"""Model Registry abstraction for clinical AI/ML models.

Stores and enforces required version quadruple:
- model_version
- training_data_version
- feature_version
- evaluation_version

Enforces stage transitions and stores model artifacts, preprocessors, and metadata.
DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ml.models.base import BaseRiskModel
from ml.preprocessing.pipeline import ClinicalDataPreprocessor


class ModelStage(str, Enum):
    EXPERIMENTAL = "EXPERIMENTAL"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


@dataclass
class RegisteredModelRecord:
    model_name: str
    model_version: str
    training_data_version: str
    feature_version: str
    evaluation_version: str
    stage: str
    created_at: str
    metrics: Dict[str, Any]
    parameters: Dict[str, Any]
    feature_names: List[str]
    model_artifact_path: str
    preprocessor_artifact_path: str
    description: str = ""
    disclaimer: str = (
        "RESEARCH DEMONSTRATION ONLY: This model version is an experimental decision-support "
        "prototype. It has not undergone clinical trials and is NOT clinically validated for "
        "autonomous diagnostic or therapeutic decisions."
    )


class ModelRegistry:
    """Persistent registry managing versioned clinical AI models and their dependencies."""

    def __init__(self, registry_dir: str = "ml/models/registry_store"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.registry_dir / "registry_index.json"
        self._ensure_index()

    def _ensure_index(self) -> None:
        if not self.index_file.exists():
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def _read_index(self) -> Dict[str, Dict[str, Any]]:
        with open(self.index_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_index(self, data: Dict[str, Dict[str, Any]]) -> None:
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _make_key(self, model_name: str, model_version: str) -> str:
        return f"{model_name}@{model_version}"

    def register_model(
        self,
        model: BaseRiskModel,
        preprocessor: ClinicalDataPreprocessor,
        model_version: str,
        training_data_version: str,
        feature_version: str,
        evaluation_version: str,
        metrics: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        description: str = "",
        stage: ModelStage = ModelStage.EXPERIMENTAL,
    ) -> RegisteredModelRecord:
        """Registers a model with required versioning quadruple and persists artifacts."""
        model_name = model.model_name
        version_dir = self.registry_dir / model_name / model_version
        version_dir.mkdir(parents=True, exist_ok=True)

        model_artifact_path = version_dir / "model.pkl"
        preprocessor_artifact_path = version_dir / "preprocessor.pkl"

        # Save artifacts
        model.save(model_artifact_path)
        preprocessor.save(preprocessor_artifact_path)

        record = RegisteredModelRecord(
            model_name=model_name,
            model_version=model_version,
            training_data_version=training_data_version,
            feature_version=feature_version,
            evaluation_version=evaluation_version,
            stage=stage.value,
            created_at=pd.Timestamp.now().isoformat() if "pd" in globals() else str(Path.stat),
            metrics=metrics,
            parameters=parameters or model.get_params(),
            feature_names=preprocessor.feature_names_out_,
            model_artifact_path=str(model_artifact_path.resolve()),
            preprocessor_artifact_path=str(preprocessor_artifact_path.resolve()),
            description=description,
        )

        import datetime
        record.created_at = datetime.datetime.now().isoformat()

        # Update index
        index = self._read_index()
        key = self._make_key(model_name, model_version)
        index[key] = asdict(record)
        self._write_index(index)

        # Also write local manifest inside model directory
        manifest_path = version_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(asdict(record), f, indent=2)

        return record

    def transition_stage(
        self,
        model_name: str,
        model_version: str,
        new_stage: ModelStage,
    ) -> RegisteredModelRecord:
        """Transitions model stage (e.g., EXPERIMENTAL -> STAGING -> PRODUCTION).
        
        If transitioned to PRODUCTION, any prior PRODUCTION model of the same name is demoted to STAGING/ARCHIVED.
        """
        index = self._read_index()
        target_key = self._make_key(model_name, model_version)

        if target_key not in index:
            raise KeyError(f"Model {target_key} not found in registry.")

        if new_stage == ModelStage.PRODUCTION:
            # Demote existing production models of the same model_name
            for key, rec_dict in index.items():
                if rec_dict["model_name"] == model_name and rec_dict["stage"] == ModelStage.PRODUCTION.value and key != target_key:
                    rec_dict["stage"] = ModelStage.ARCHIVED.value

        index[target_key]["stage"] = new_stage.value
        self._write_index(index)

        return RegisteredModelRecord(**index[target_key])

    def get_model_record(self, model_name: str, model_version: str) -> RegisteredModelRecord:
        """Retrieve metadata record for specific version."""
        index = self._read_index()
        key = self._make_key(model_name, model_version)
        if key not in index:
            raise KeyError(f"Model {key} not found in registry.")
        return RegisteredModelRecord(**index[key])

    def get_production_record(self, model_name: str) -> Optional[RegisteredModelRecord]:
        """Retrieve current production version metadata for model."""
        index = self._read_index()
        for rec_dict in index.values():
            if rec_dict["model_name"] == model_name and rec_dict["stage"] == ModelStage.PRODUCTION.value:
                return RegisteredModelRecord(**rec_dict)
        return None

    def list_models(
        self,
        model_name: Optional[str] = None,
        stage: Optional[Union[str, ModelStage]] = None,
    ) -> List[RegisteredModelRecord]:
        """List registered model records filtered by name or stage."""
        index = self._read_index()
        results = []
        stage_val = stage.value if isinstance(stage, ModelStage) else stage

        for rec_dict in index.values():
            if model_name and rec_dict["model_name"] != model_name:
                continue
            if stage_val and rec_dict["stage"] != stage_val:
                continue
            results.append(RegisteredModelRecord(**rec_dict))
        return results

    def load_bundle(
        self,
        model_name: str,
        model_version: Optional[str] = None,
    ) -> Tuple[Any, ClinicalDataPreprocessor, RegisteredModelRecord]:
        """Loads model artifact, preprocessor, and metadata record.
        
        If model_version is None, loads the current PRODUCTION model.
        """
        if model_version is None:
            record = self.get_production_record(model_name)
            if record is None:
                raise ValueError(f"No active PRODUCTION model found for {model_name}.")
        else:
            record = self.get_model_record(model_name, model_version)

        import pickle
        with open(record.model_artifact_path, "rb") as f:
            model = pickle.load(f)
        preprocessor = ClinicalDataPreprocessor.load(record.preprocessor_artifact_path)

        return model, preprocessor, record
