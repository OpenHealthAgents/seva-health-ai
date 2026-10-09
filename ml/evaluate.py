"""Reproducible evaluation script for SevaHealth AI clinical risk models.

Computes discrimination (AUROC, AUPRC), clinical rates (sensitivity, specificity, PPV, NPV),
calibration (ECE, MCE, Brier score, slope, intercept), confusion matrix,
demographic slices (by age, sex, demographic groups), and missing-data sensitivity stress tests.
Generates comprehensive Model Card.

Usage:
    python ml/evaluate.py --model-name calibrated_gradient_boosting_risk_model --model-version v1.0.0

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from ml.datasets.dataset_loader import DatasetLoader
from ml.evaluation.evaluator import ModelEvaluator
from ml.features.feature_engineering import ClinicalFeatureEngineer
from ml.model_cards.generator import ModelCardGenerator
from ml.models.registry import ModelRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ml_evaluate")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Evaluate SevaHealth AI Clinical Risk Model")
    parser.add_argument(
        "--model-name",
        type=str,
        default="calibrated_gradient_boosting_risk_model",
        help="Name of model to evaluate",
    )
    parser.add_argument("--model-version", type=str, default=None, help="Model version (defaults to PRODUCTION)")
    parser.add_argument("--data-version", type=str, default="v1.0.0", help="Test dataset version")
    parser.add_argument("--eval-version", type=str, default="v1.0.0", help="Evaluation version tag")
    parser.add_argument("--threshold", type=float, default=0.5, help="Decision threshold")

    args = parser.parse_args()

    # 1. Load Model Bundle from Registry
    registry = ModelRegistry()
    logger.info(f"Loading model '{args.model_name}' (version: {args.model_version or 'PRODUCTION'})...")
    model, preprocessor, record = registry.load_bundle(args.model_name, args.model_version)
    logger.info(
        f"Loaded model '{record.model_name}' v{record.model_version} "
        f"[Stage: {record.stage}, Trained on data: {record.training_data_version}, Features: {record.feature_version}]"
    )

    # 2. Load Test Dataset
    loader = DatasetLoader()
    test_path = loader.data_dir / f"test_cohort_{record.training_data_version}.csv"
    if test_path.exists():
        logger.info(f"Loading test cohort from {test_path}...")
        df_test = pd.read_csv(test_path)
    else:
        logger.info(f"Test cohort not found on disk, loading full cohort and splitting...")
        df_full, _ = loader.load_or_generate_synthetic(version=record.training_data_version)
        _, _, df_test = loader.get_train_val_test_splits(df_full)

    logger.info(f"Evaluating on {len(df_test)} test patients...")

    # 3. Run Evaluation Suite
    feature_engineer = ClinicalFeatureEngineer(feature_version=record.feature_version)
    evaluator = ModelEvaluator(evaluation_version=args.eval_version)

    report = evaluator.evaluate(
        model=model,
        preprocessor=preprocessor,
        feature_engineer=feature_engineer,
        test_df=df_test,
        decision_threshold=args.threshold,
        training_data_version=record.training_data_version,
        feature_version=record.feature_version,
    )

    # 4. Save Evaluation Reports
    reports_dir = Path("ml/evaluation/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"eval_{record.model_name}_{record.model_version}.json"
    md_path = reports_dir / f"eval_{record.model_name}_{record.model_version}.md"

    report.save_json(json_path)
    md_summary = report.generate_markdown_summary()
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_summary)

    logger.info(f"Evaluation report JSON saved to {json_path}")
    logger.info(f"Evaluation report Markdown saved to {md_path}")

    # 5. Generate and Save Model Card
    logger.info("Generating Model Card...")
    card_data = ModelCardGenerator.from_evaluation_report(report)
    
    cards_dir = Path("ml/model_cards")
    cards_dir.mkdir(parents=True, exist_ok=True)
    card_json_path = cards_dir / f"card_{record.model_name}_{record.model_version}.json"
    card_md_path = cards_dir / f"card_{record.model_name}_{record.model_version}.md"

    card_data.save_json(card_json_path)
    with open(card_md_path, "w", encoding="utf-8") as f:
        f.write(card_data.generate_markdown())

    logger.info(f"Model Card JSON saved to {card_json_path}")
    logger.info(f"Model Card Markdown saved to {card_md_path}")

    # Output Markdown summary to console
    print("\n" + "=" * 80)
    print(md_summary)
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
