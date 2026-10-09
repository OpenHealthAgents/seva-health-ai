"""Model Card generator for clinical machine learning models.

Documents:
- Intended Use
- Limitations
- Target Population
- Input Features & Preprocessing
- Quantitative Performance & Fairness Disparities
- Known Risks & Ethical Considerations
- Clinical Non-Validation Disclaimer

DISCLAIMER: For research and demonstration purposes only. Not clinically validated.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ml.evaluation.evaluator import CompleteEvaluationReport


@dataclass
class ModelCardData:
    model_name: str
    model_version: str
    training_data_version: str
    feature_version: str
    evaluation_version: str
    date_created: str
    intended_use: Dict[str, Any]
    limitations: List[str]
    population: Dict[str, Any]
    features: List[str]
    performance_summary: Dict[str, Any]
    known_risks: List[str]
    clinical_validation_disclaimer: str = (
        "DO NOT CLAIM CLINICAL VALIDATION. This model is a research prototype developed for "
        "decision-support exploration in community screening settings. It has NOT undergone clinical "
        "trials, has not received regulatory clearance (such as FDA 510(k), CE-IVD, or CDSCO MD-42), "
        "and is strictly prohibited from autonomous clinical triage, acute diagnosis, or medication dosing."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_json(self, filepath: Union[str, Path]) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def generate_markdown(self) -> str:
        lines = [
            f"# Model Card: {self.model_name}",
            "",
            "| Version Attribute | Version String |",
            "|---|---|",
            f"| **Model Version** | `{self.model_version}` |",
            f"| **Training Data Version** | `{self.training_data_version}` |",
            f"| **Feature Version** | `{self.feature_version}` |",
            f"| **Evaluation Version** | `{self.evaluation_version}` |",
            f"| **Release Date** | {self.date_created} |",
            "",
            "---",
            "",
            "> ⚠️ **REGULATORY & CLINICAL VALIDATION DISCLAIMER**",
            "> ",
            f"> {self.clinical_validation_disclaimer}",
            "",
            "---",
            "",
            "## 1. Intended Use",
            f"- **Primary Purpose**: {self.intended_use.get('primary_purpose', 'Demonstration risk stratification')}",
            f"- **Target Users**: {', '.join(self.intended_use.get('target_users', []))}",
            f"- **Intended Care Setting**: {self.intended_use.get('care_setting', 'Community screening and outpatient health camps')}",
            "",
            "### Out-of-Scope & Prohibited Uses",
        ]

        for out_use in self.intended_use.get("out_of_scope_uses", []):
            lines.append(f"- ⛔ {out_use}")

        lines.extend([
            "",
            "## 2. Target Population & Cohort Demographics",
            f"- **Target Age Range**: {self.population.get('age_range', 'Adults 18-85 years')}",
            f"- **Regional Representation**: {', '.join(self.population.get('regions', []))}",
            f"- **Disease Prevalence in Cohort**: {self.population.get('prevalence', 'Estimated ~18-22%')}",
            f"- **Inclusion Criteria**: {self.population.get('inclusion_criteria', 'Adult screening attendees with at least basic vitals recorded')}",
            f"- **Exclusion Criteria**: {self.population.get('exclusion_criteria', 'Prior acute coronary syndrome within 30 days, pregnancy, end-stage renal failure on dialysis')}",
            "",
            "## 3. Model Inputs & Engineered Features",
            f"Total input features: **{len(self.features)}**",
            "",
            "```",
            ", ".join(self.features),
            "```",
            "",
            "## 4. Quantitative Performance Metrics",
            "### Overall Test Set Metrics",
            "| Metric | Value |",
            "|---|---|",
        ])

        for k, v in self.performance_summary.get("overall_metrics", {}).items():
            if isinstance(v, float):
                lines.append(f"| {k.replace('_', ' ').title()} | {v:.4f} |")
            else:
                lines.append(f"| {k.replace('_', ' ').title()} | {v} |")

        lines.extend([
            "",
            "### Demographic Disparity & Fairness",
        ])
        for k, v in self.performance_summary.get("demographic_disparities", {}).items():
            lines.append(f"- **{k.replace('_', ' ').title()}**: `{v}`")

        lines.extend([
            "",
            "### Missing-Data Sensitivity",
            f"- **Missingness Robustness**: {self.performance_summary.get('missingness_summary', 'Evaluated across 10%-75% feature missingness')}",
            "",
            "## 5. Model Limitations",
        ])
        for lim in self.limitations:
            lines.append(f"- ⚠️ {lim}")

        lines.extend([
            "",
            "## 6. Known Risks & Ethical Considerations",
        ])
        for risk in self.known_risks:
            lines.append(f"- ❗ {risk}")

        lines.extend([
            "",
            "## 7. Model Governance & Maintenance Plan",
            "- **Retraining Frequency**: Bi-annual or when data distribution drift exceeds PSI > 0.25.",
            "- **Drift Monitoring**: Continuous tracking of mean arterial pressure distribution and lab testing availability.",
            "- **Human-in-the-Loop Requirement**: All flagged high-risk alerts must be validated by a registered medical officer.",
        ])

        return "\n".join(lines)


class ModelCardGenerator:
    """Generates standardized model cards from evaluation reports and clinical metadata."""

    @classmethod
    def from_evaluation_report(
        cls,
        report: CompleteEvaluationReport,
        intended_use: Optional[Dict[str, Any]] = None,
        limitations: Optional[List[str]] = None,
        population: Optional[Dict[str, Any]] = None,
        known_risks: Optional[List[str]] = None,
    ) -> ModelCardData:
        default_intended_use = {
            "primary_purpose": "Demonstration early-warning cardiometabolic risk stratification for community health screenings.",
            "target_users": ["Community Health Workers (ASHAs)", "Primary Care Nurses", "Preventive Health Officers"],
            "care_setting": "Community primary health centers and rural screening camps.",
            "out_of_scope_uses": [
                "Autonomous diagnosis of acute coronary syndrome or stroke.",
                "Automated prescription or alteration of anti-hypertensive or anti-diabetic medication.",
                "Standalone clinical decision-making without physician oversight.",
            ],
        }

        default_limitations = [
            "Trained and evaluated on synthetic demonstration cohorts simulating epidemiological distributions.",
            "Does NOT incorporate serial ECG waveforms, continuous telemetry, or genomic polygenic risk scores.",
            "Laboratory biomarker imputation assumes missingness patterns observed in demonstration data; extreme unmeasured covariates may degrade accuracy.",
            "Predictions reflect statistical risk association rather than causal individual pathophysiology.",
        ]

        default_population = {
            "age_range": "18 to 85 years",
            "regions": ["North-Rural", "North-Urban", "South-Rural", "South-Urban", "East-Rural", "East-Urban", "West-Rural", "West-Urban"],
            "prevalence": f"{report.overall_metrics.prevalence*100:.1f}% positive event rate in cohort",
            "inclusion_criteria": "Adults participating in preventive cardiometabolic health screening.",
            "exclusion_criteria": "Active emergency symptoms (chest pain, shock), pregnancy, pediatric population (<18y).",
        }

        default_known_risks = [
            "Risk of False Negatives: Patient with atypical presentation may receive Low Risk rating, delaying clinical referral.",
            "Risk of False Positives: Healthy patient flagged as High Risk may experience psychological distress and unnecessary secondary care referral.",
            "Demographic Disparity: Resource-constrained rural clinics lacking point-of-care lab tests will experience moderate sensitivity drop.",
            "Over-reliance / Automation Bias: Clinicians must not treat risk scores as definitive diagnostic findings.",
        ]

        om = report.overall_metrics
        perf_summary = {
            "overall_metrics": {
                "auroc": om.auroc,
                "auprc": om.auprc,
                "sensitivity": om.sensitivity,
                "specificity": om.specificity,
                "ppv": om.ppv,
                "npv": om.npv,
                "brier_score": om.calibration.brier_score,
                "expected_calibration_error": om.calibration.expected_calibration_error,
                "optimal_threshold": report.optimal_threshold,
            },
            "demographic_disparities": report.demographic_evaluation.disparity_summary,
            "missingness_summary": report.missing_data_sensitivity.resilience_summary,
        }

        feature_names = [
            "age",
            "sex",
            "demographic_group",
            "bmi",
            "systolic_bp",
            "diastolic_bp",
            "heart_rate",
            "fasting_glucose",
            "hba1c",
            "total_cholesterol",
            "hdl_cholesterol",
            "ldl_cholesterol",
            "triglycerides",
            "serum_creatinine",
            "smoking_status",
            "physical_activity",
            "family_history",
            "mean_arterial_pressure",
            "pulse_pressure",
            "cholesterol_hdl_ratio",
            "triglyceride_hdl_ratio",
            "hypertension_stage",
            "glycemic_risk_flag",
            "metabolic_syndrome_score",
        ]

        return ModelCardData(
            model_name=report.model_name,
            model_version=report.model_version,
            training_data_version=report.training_data_version,
            feature_version=report.feature_version,
            evaluation_version=report.evaluation_version,
            date_created=report.timestamp[:10],
            intended_use=intended_use or default_intended_use,
            limitations=limitations or default_limitations,
            population=population or default_population,
            features=feature_names,
            performance_summary=perf_summary,
            known_risks=known_risks or default_known_risks,
        )
