"""Comprehensive test suite for the SevaHealth AI ML experimentation framework.

Tests:
- Synthetic demonstration cohort generation and metadata tracking
- Clinical data preprocessing with outlier clipping and imputation
- Clinical feature engineering (MAP, pulse pressure, lipid ratios, MetS score)
- Model training, calibration, and classification
- Model registry version quadruple (model, data, feature, eval) and stage lifecycle
- Complete evaluation metrics (AUROC, AUPRC, sensitivity, specificity, PPV, NPV, Brier, ECE, CM)
- Demographic subgroup evaluation (age, sex, demographic groups)
- Missing-data sensitivity stress tests (random missingness & panel dropouts)
- Inference engine real-time and batch scoring
- Model card generation and non-clinical validation disclaimers
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.datasets.dataset_loader import DatasetLoader
from ml.datasets.synthetic_generator import SyntheticCohortGenerator
from ml.evaluation.demographics import DemographicEvaluator
from ml.evaluation.evaluator import ModelEvaluator
from ml.evaluation.metrics import ClinicalMetricsCalculator
from ml.evaluation.missingness import MissingDataSensitivityAnalyzer
from ml.features.feature_engineering import ClinicalFeatureEngineer
from ml.inference.engine import RiskInferenceEngine
from ml.model_cards.generator import ModelCardGenerator
from ml.models.classifiers import (
    CalibratedRiskModel,
    EnsembleRiskModel,
    LogisticRiskModel,
)
from ml.models.registry import ModelRegistry, ModelStage
from ml.models.trainer import ModelTrainer
from ml.preprocessing.pipeline import ClinicalDataPreprocessor


class TestMLFramework:
    """Test suite for SevaHealth AI ML experimentation framework."""

    @pytest.fixture
    def cohort_data(self):
        generator = SyntheticCohortGenerator(random_state=42)
        df, metadata = generator.generate(n_samples=500, missing_rate=0.05, data_version="v1.0.0-test")
        return df, metadata

    def test_synthetic_cohort_generator(self, cohort_data):
        df, metadata = cohort_data
        assert len(df) == 500
        assert metadata.data_version == "v1.0.0-test"
        assert metadata.positive_rate > 0.0
        assert "clinically validated" in metadata.disclaimer.lower()

        # Check required columns
        expected_cols = [
            "patient_id", "age", "sex", "demographic_group", "bmi",
            "systolic_bp", "diastolic_bp", "heart_rate", "fasting_glucose",
            "hba1c", "total_cholesterol", "hdl_cholesterol", "event_outcome"
        ]
        for col in expected_cols:
            assert col in df.columns

        # Verify age and vitals ranges
        assert df["age"].min() >= 18.0
        assert df["age"].max() <= 85.0
        assert df["systolic_bp"].min() >= 80.0

    def test_clinical_feature_engineering(self, cohort_data):
        df, _ = cohort_data
        engineer = ClinicalFeatureEngineer(feature_version="v1.0.0-fe")
        fe_df = engineer.transform(df)

        # Verify derived clinical features exist
        assert "mean_arterial_pressure" in fe_df.columns
        assert "pulse_pressure" in fe_df.columns
        assert "cholesterol_hdl_ratio" in fe_df.columns
        assert "triglyceride_hdl_ratio" in fe_df.columns
        assert "hypertension_stage" in fe_df.columns
        assert "glycemic_risk_flag" in fe_df.columns
        assert "metabolic_syndrome_score" in fe_df.columns
        assert "cvd_age_bp_interaction" in fe_df.columns

        # Verify mathematical consistency
        row = fe_df.dropna(subset=["systolic_bp", "diastolic_bp"]).iloc[0]
        expected_map = (2.0 * row["diastolic_bp"] + row["systolic_bp"]) / 3.0
        assert abs(row["mean_arterial_pressure"] - expected_map) < 1e-4

        expected_pp = row["systolic_bp"] - row["diastolic_bp"]
        assert abs(row["pulse_pressure"] - expected_pp) < 1e-4

    def test_preprocessing_pipeline(self, cohort_data):
        df, _ = cohort_data
        engineer = ClinicalFeatureEngineer()
        fe_df = engineer.transform(df)

        drop_cols = ["patient_id", "event_outcome"]
        clean_df = fe_df.drop(columns=[c for c in drop_cols if c in fe_df.columns])

        preprocessor = ClinicalDataPreprocessor(
            preprocessing_version="v1.0.0",
            imputation_strategy="median",
            add_indicator_for_missing=True,
            clip_outliers=True,
            scaler_type="standard",
        )

        proc_train = preprocessor.fit_transform(clean_df)
        assert preprocessor.is_fitted
        assert proc_train.isna().sum().sum() == 0  # Imputed completely
        assert "systolic_bp_is_missing" in proc_train.columns

        # Test persistence
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "preprocessor.pkl"
            preprocessor.save(save_path)
            loaded = ClinicalDataPreprocessor.load(save_path)
            assert loaded.is_fitted
            proc_loaded = loaded.transform(clean_df.head(10))
            assert proc_loaded.shape == proc_train.head(10).shape

    def test_model_training_and_calibration(self, cohort_data):
        df, _ = cohort_data
        loader = DatasetLoader()
        df_train, df_val, df_test = loader.get_train_val_test_splits(df, test_size=0.2, val_size=0.2)

        trainer = ModelTrainer(
            model_version="v1.0.0-test",
            training_data_version="v1.0.0-test",
            feature_version="v1.0.0-test",
            evaluation_version="v1.0.0-test",
        )

        # Train calibrated ensemble
        result = trainer.train(
            train_df=df_train,
            val_df=df_val,
            model_type="calibrated_ensemble",
            target_col="event_outcome",
        )

        assert result.model.is_fitted
        assert "auroc" in result.val_metrics
        assert "brier_score" in result.val_metrics

        # Test predict and predict_proba contract
        fe = result.feature_engineer
        prep = result.preprocessor
        test_fe = fe.transform(df_test)
        clean_test = test_fe.drop(columns=["patient_id", "event_outcome"], errors="ignore")
        X_test_proc = prep.transform(clean_test)

        probs = result.model.predict_proba(X_test_proc)
        assert probs.shape == (len(df_test), 2)
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0)

        preds = result.model.predict(X_test_proc, threshold=0.1)
        assert len(preds) == len(df_test)
        assert set(preds).issubset({0, 1})

    def test_model_registry_version_quadruple(self, cohort_data):
        df, _ = cohort_data
        loader = DatasetLoader()
        df_train, df_val, _ = loader.get_train_val_test_splits(df)

        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(registry_dir=tmpdir)
            trainer = ModelTrainer(
                model_version="v1.0.0",
                training_data_version="d1.0.0",
                feature_version="f1.0.0",
                evaluation_version="e1.0.0",
                registry=registry,
            )

            result, record = trainer.train_and_register(
                train_df=df_train,
                val_df=df_val,
                model_type="logistic",
                stage=ModelStage.PRODUCTION,
            )

            # Assert all 4 required versions are stored
            assert record.model_version == "v1.0.0"
            assert record.training_data_version == "d1.0.0"
            assert record.feature_version == "f1.0.0"
            assert record.evaluation_version == "e1.0.0"
            assert record.stage == ModelStage.PRODUCTION.value
            assert "NOT clinically validated" in record.disclaimer

            # Verify bundle loading
            loaded_model, loaded_prep, loaded_rec = registry.load_bundle("logistic_risk_model")
            assert loaded_rec.model_version == "v1.0.0"
            assert loaded_model.is_fitted
            assert loaded_prep.is_fitted

            # Test stage transition
            registry.transition_stage("logistic_risk_model", "v1.0.0", ModelStage.ARCHIVED)
            updated_rec = registry.get_model_record("logistic_risk_model", "v1.0.0")
            assert updated_rec.stage == ModelStage.ARCHIVED.value

    def test_clinical_metrics_calculator(self):
        y_true = np.array([0, 0, 0, 1, 0, 1, 1, 0, 1, 0])
        y_prob = np.array([0.1, 0.2, 0.15, 0.8, 0.3, 0.65, 0.9, 0.05, 0.7, 0.25])

        metrics = ClinicalMetricsCalculator.compute_all_metrics(y_true, y_prob, threshold=0.5)

        assert 0.0 <= metrics.auroc <= 1.0
        assert 0.0 <= metrics.auprc <= 1.0
        assert 0.0 <= metrics.sensitivity <= 1.0
        assert 0.0 <= metrics.specificity <= 1.0
        assert 0.0 <= metrics.ppv <= 1.0
        assert 0.0 <= metrics.npv <= 1.0
        assert metrics.calibration.brier_score >= 0.0
        assert metrics.calibration.expected_calibration_error >= 0.0
        assert metrics.confusion_matrix.total == 10

        # Check optimal threshold finder
        opt_thresh = ClinicalMetricsCalculator.find_optimal_threshold(y_true, y_prob, metric="youden")
        assert 0.05 <= opt_thresh <= 0.95

    def test_demographic_fairness_evaluation(self, cohort_data):
        df, _ = cohort_data
        y_prob = np.random.uniform(0.05, 0.45, size=len(df))

        report = DemographicEvaluator.evaluate_subgroups(
            df_raw=df,
            y_prob=y_prob,
            target_col="event_outcome",
            threshold=0.2,
        )

        assert len(report.performance_by_age) > 0
        assert len(report.performance_by_sex) >= 2
        assert len(report.performance_by_demographic_groups) > 0
        assert "NOT clinically validated" in report.disclaimer

        for sub in report.performance_by_sex:
            assert sub.attribute_name == "sex"
            assert sub.sample_size > 0
            assert sub.auroc >= 0.0

    def test_missing_data_sensitivity(self, cohort_data):
        df, _ = cohort_data
        loader = DatasetLoader()
        df_train, df_val, df_test = loader.get_train_val_test_splits(df)

        trainer = ModelTrainer()
        result = trainer.train(df_train, df_val, model_type="logistic")

        analyzer = MissingDataSensitivityAnalyzer(
            model=result.model,
            preprocessor=result.preprocessor,
            feature_engineer=result.feature_engineer,
        )

        report = analyzer.evaluate(test_df_raw=df_test, threshold=0.1)
        assert len(report.rate_sensitivity_curve) >= 4
        assert len(report.panel_dropout_evaluations) >= 2
        assert "NOT clinically validated" in report.disclaimer
        assert "laboratory" in report.panel_dropout_evaluations[0].condition_name.lower()

    def test_risk_inference_engine(self, cohort_data):
        df, _ = cohort_data
        loader = DatasetLoader()
        df_train, df_val, _ = loader.get_train_val_test_splits(df)

        trainer = ModelTrainer(model_version="v1.0.0")
        result = trainer.train(df_train, df_val, model_type="calibrated_ensemble")

        engine = RiskInferenceEngine(
            model=result.model,
            preprocessor=result.preprocessor,
            feature_engineer=result.feature_engineer,
            model_version="v1.0.0",
            training_data_version="v1.0.0",
            feature_version="v1.0.0",
            evaluation_version="v1.0.0",
        )

        patient_record = {
            "patient_id": "TEST-001",
            "age": 58,
            "sex": "Male",
            "demographic_group": "North-Rural",
            "bmi": 28.5,
            "systolic_bp": 145,
            "diastolic_bp": 92,
            "heart_rate": 78,
            "fasting_glucose": 135,
            "hba1c": 7.1,
            "total_cholesterol": 220,
            "hdl_cholesterol": 38,
            "ldl_cholesterol": 140,
            "triglycerides": 210,
            "smoking_status": 1,
            "physical_activity": 0,
            "family_history": 1,
        }

        assessment = engine.predict_patient(patient_record)
        assert assessment.patient_id == "TEST-001"
        assert 0.0 <= assessment.predicted_probability <= 1.0
        assert assessment.risk_tier in ["Low", "Moderate", "High", "Critical"]
        assert len(assessment.confidence_interval_95) == 2
        assert len(assessment.top_risk_factors) > 0
        assert "NOT been clinically validated" in assessment.disclaimer

    def test_model_card_generation(self, cohort_data):
        df, _ = cohort_data
        loader = DatasetLoader()
        df_train, df_val, df_test = loader.get_train_val_test_splits(df)

        trainer = ModelTrainer(
            model_version="v1.0.0",
            training_data_version="d1.0.0",
            feature_version="f1.0.0",
            evaluation_version="e1.0.0",
        )
        result = trainer.train(df_train, df_val, model_type="logistic")

        evaluator = ModelEvaluator(evaluation_version="e1.0.0")
        report = evaluator.evaluate(
            model=result.model,
            preprocessor=result.preprocessor,
            feature_engineer=result.feature_engineer,
            test_df=df_test,
            decision_threshold=0.2,
            training_data_version="d1.0.0",
            feature_version="f1.0.0",
        )

        card_data = ModelCardGenerator.from_evaluation_report(report)
        md_text = card_data.generate_markdown()

        # Check required sections per prompt
        assert "# Model Card:" in md_text
        assert "Intended Use" in md_text
        assert "Limitations" in md_text
        assert "Target Population" in md_text
        assert "Model Inputs & Engineered Features" in md_text
        assert "Quantitative Performance Metrics" in md_text
        assert "Known Risks & Ethical Considerations" in md_text
        assert "DO NOT CLAIM CLINICAL VALIDATION" in md_text
        assert "v1.0.0" in md_text
        assert "d1.0.0" in md_text
        assert "f1.0.0" in md_text
        assert "e1.0.0" in md_text
