"""Reproducible training script for SevaHealth AI clinical risk models.

Usage:
    python ml/train.py --n-samples 5000 --model-version v1.0.0 --model-type calibrated_ensemble

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.datasets.dataset_loader import DatasetLoader
from ml.models.registry import ModelRegistry, ModelStage
from ml.models.trainer import ModelTrainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ml_train")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train SevaHealth AI Clinical Risk Model")
    parser.add_argument("--n-samples", type=int, default=5000, help="Number of synthetic samples")
    parser.add_argument("--missing-rate", type=float, default=0.08, help="Missing rate in synthetic cohort")
    parser.add_argument("--model-version", type=str, default="v1.0.0", help="Model version tag")
    parser.add_argument("--data-version", type=str, default="v1.0.0", help="Training data version tag")
    parser.add_argument("--feature-version", type=str, default="v1.0.0", help="Feature version tag")
    parser.add_argument("--evaluation-version", type=str, default="v1.0.0", help="Evaluation version tag")
    parser.add_argument(
        "--model-type",
        type=str,
        default="calibrated_ensemble",
        choices=["logistic", "ensemble", "calibrated_logistic", "calibrated_ensemble"],
        help="Algorithm type",
    )
    parser.add_argument("--promote-production", action="store_true", default=True, help="Promote trained model to PRODUCTION")

    args = parser.parse_args()

    logger.info("Initializing synthetic dataset loader...")
    loader = DatasetLoader()
    df, metadata = loader.load_or_generate_synthetic(
        n_samples=args.n_samples,
        missing_rate=args.missing_rate,
        version=args.data_version,
    )
    logger.info(
        f"Dataset loaded: {metadata.num_samples} records, "
        f"{metadata.positive_rate*100:.1f}% positive prevalence, Checksum: {metadata.checksum[:10]}..."
    )

    df_train, df_val, df_test = loader.get_train_val_test_splits(df)
    logger.info(
        f"Splits created: Train={len(df_train)}, Validation={len(df_val)}, Test={len(df_test)}"
    )

    # Save test set for reproducible evaluation
    test_path = loader.data_dir / f"test_cohort_{args.data_version}.csv"
    df_test.to_csv(test_path, index=False)
    logger.info(f"Test cohort saved to {test_path}")

    # Initialize Registry and Trainer
    registry = ModelRegistry()
    trainer = ModelTrainer(
        model_version=args.model_version,
        training_data_version=args.data_version,
        feature_version=args.feature_version,
        evaluation_version=args.evaluation_version,
        registry=registry,
    )

    logger.info(f"Training {args.model_type} model (version {args.model_version})...")
    stage = ModelStage.PRODUCTION if args.promote_production else ModelStage.EXPERIMENTAL

    result, record = trainer.train_and_register(
        train_df=df_train,
        val_df=df_val,
        model_type=args.model_type,
        stage=stage,
        description=f"Model trained with {args.model_type} on cohort {args.data_version}.",
    )

    logger.info("Training complete!")
    logger.info(f"Validation AUROC: {result.val_metrics['auroc']:.4f}")
    logger.info(f"Validation Brier: {result.val_metrics['brier_score']:.4f}")
    logger.info(f"Model registered successfully in registry at stage: {record.stage}")
    logger.info(f"Artifact location: {record.model_artifact_path}")


if __name__ == "__main__":
    main()
