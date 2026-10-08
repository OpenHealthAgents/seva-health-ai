from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from packages.types.enums import RiskTier, TrajectoryTrend
from packages.clinical_models.risk import DomainRiskScores, RiskDriver, ProtectiveFactor
from packages.clinical_models.observations import Observation
from services.wearable.models import WearableProjection
from services.risk_engine.base import (
    RiskModel,
    RiskCategory,
    ImpactDirection,
    DomainRiskResult,
    RiskFactorContribution,
)
from services.risk_engine.models.diabetes import DiabetesRiskModel
from services.risk_engine.models.hypertension import HypertensionRiskModel
from services.risk_engine.models.cardiovascular import CardiovascularRiskModel
from services.risk_engine.models.obesity import ObesityMetabolicRiskModel
from services.risk_engine.models.ckd import CKDRiskModel


class ModularRiskAssessment(BaseModel):
    overall_score: Optional[float] = None
    overall_category: RiskCategory
    confidence: float
    trajectory: TrajectoryTrend
    domain_results: Dict[str, DomainRiskResult]
    top_drivers: List[RiskFactorContribution] = []
    protective_factors: List[RiskFactorContribution] = []
    limitations: List[str] = []
    recommended_next_steps: List[str] = []
    clinical_summary: str
    clinical_safety_notice: str = (
        "SAFETY NOTICE: Risk estimation is NOT diagnosis. This score indicates statistical "
        "and guideline-based probability. It does NOT independently diagnose illness or prescribe therapy. "
        "High-risk assessments require qualified clinical evaluation."
    )
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NCDRiskEngine:
    """Central orchestration engine for SevaHealth NCD Risk Models.
    
    Coordinates domain-specific models:
    1. Diabetes & Glycemic Risk (ICMR-INDIAB 2023 & IDRS)
    2. Hypertension & Vascular Risk (ACC/AHA 2017 & ICMR)
    3. Cardiovascular 10-Year ASCVD Risk (WHO-SEAR 2019)
    4. Obesity & Metabolic Syndrome (WHO South Asian Cutoffs & ICMR)
    5. Chronic Kidney Disease (KDIGO 2024 & CKD-EPI 2021)
    """

    # Domain weighting for composite risk calculation
    DOMAIN_WEIGHTS = {
        "diabetes": 0.25,
        "hypertension": 0.25,
        "cardiovascular": 0.25,
        "obesity": 0.15,
        "ckd": 0.10,
    }

    def __init__(self):
        self._models: Dict[str, RiskModel] = {
            "diabetes": DiabetesRiskModel(),
            "hypertension": HypertensionRiskModel(),
            "cardiovascular": CardiovascularRiskModel(),
            "obesity": ObesityMetabolicRiskModel(),
            "ckd": CKDRiskModel(),
        }

    def register_model(self, key: str, model: RiskModel):
        self._models[key] = model

    def get_model(self, key: str) -> Optional[RiskModel]:
        return self._models.get(key)

    def list_models(self) -> List[Dict[str, Any]]:
        catalog = []
        for key, model in self._models.items():
            catalog.append({
                "key": key,
                "domain": model.domain,
                "version": model.version(),
                "is_clinically_validated": model.is_clinically_validated(),
                "provenance": model.provenance(),
                "required_inputs": model.required_inputs(),
                "optional_inputs": model.optional_inputs(),
                "limitations": model.limitations(),
            })
        return catalog

    def evaluate(
        self,
        raw_inputs: Dict[str, Any],
        wearable_projection: Optional[WearableProjection] = None,
    ) -> ModularRiskAssessment:
        """Evaluates all registered clinical risk models, normalizes metrics,
        and aggregates explainable contributions and trajectory.
        """
        domain_results: Dict[str, DomainRiskResult] = {}
        all_drivers: List[RiskFactorContribution] = []
        all_protective: List[RiskFactorContribution] = []
        all_limitations: List[str] = []
        all_next_steps: List[str] = []

        # Run each domain model
        for key, model in self._models.items():
            result = model.calculate(raw_inputs)
            domain_results[key] = result
            
            # Aggregate limitations
            all_limitations.extend(result.limitations)
            if result.recommended_next_step:
                all_next_steps.append(f"{model.domain}: {result.recommended_next_step}")

            # Collect feature contributions
            for contrib in result.risk_factor_contributions:
                if contrib.impact_direction == ImpactDirection.INCREASES_RISK:
                    all_drivers.append(contrib)
                elif contrib.impact_direction == ImpactDirection.DECREASES_RISK:
                    all_protective.append(contrib)

        # Sort drivers by absolute impact weight descending
        all_drivers.sort(key=lambda d: d.impact_weight, reverse=True)
        all_protective.sort(key=lambda p: abs(p.impact_weight), reverse=True)

        # Calculate composite score across domains with valid scores
        total_weight = 0.0
        weighted_score_sum = 0.0
        conf_sum = 0.0

        for key, res in domain_results.items():
            conf_sum += res.confidence
            if res.score is not None and res.risk_category != RiskCategory.INSUFFICIENT_DATA:
                w = self.DOMAIN_WEIGHTS.get(key, 0.20)
                weighted_score_sum += res.score * w
                total_weight += w

        if total_weight > 0:
            composite_score = round(weighted_score_sum / total_weight, 3)
            if composite_score >= 0.55:
                overall_category = RiskCategory.HIGH
            elif composite_score >= 0.25:
                overall_category = RiskCategory.MODERATE
            else:
                overall_category = RiskCategory.LOW
        else:
            composite_score = None
            overall_category = RiskCategory.INSUFFICIENT_DATA

        avg_confidence = round(conf_sum / len(self._models), 2) if self._models else 0.0

        # Trajectory determination (modulated by wearable trends if available)
        trajectory = self._determine_trajectory(overall_category, all_drivers, wearable_projection)

        # Build composite clinical summary
        if overall_category == RiskCategory.INSUFFICIENT_DATA:
            clinical_summary = "Insufficient clinical observations available to formulate composite risk estimate."
        else:
            top_str = all_drivers[0].feature if all_drivers else "standard population risk markers"
            clinical_summary = (
                f"Citizen exhibits {overall_category.value} composite NCD risk "
                f"({composite_score*100:.0f}% multi-domain index). "
                f"Top contributing risk factor is {top_str}. "
                f"Longitudinal trajectory is {trajectory.value}."
            )

        return ModularRiskAssessment(
            overall_score=composite_score,
            overall_category=overall_category,
            confidence=avg_confidence,
            trajectory=trajectory,
            domain_results=domain_results,
            top_drivers=all_drivers,
            protective_factors=all_protective,
            limitations=list(dict.fromkeys(all_limitations)),  # deduplicate
            recommended_next_steps=all_next_steps,
            clinical_summary=clinical_summary,
        )

    def _determine_trajectory(
        self,
        overall_category: RiskCategory,
        drivers: List[RiskFactorContribution],
        wearable_projection: Optional[WearableProjection] = None,
    ) -> TrajectoryTrend:
        """Determines longitudinal risk trajectory with wearable modulation."""
        base_trend = TrajectoryTrend.STABLE

        if overall_category == RiskCategory.HIGH:
            base_trend = TrajectoryTrend.DETERIORATING
        elif overall_category == RiskCategory.LOW:
            base_trend = TrajectoryTrend.STABLE

        # Wearable modulation
        if wearable_projection:
            # If wearable indicates active lifestyle / high adherence
            if wearable_projection.step_target_adherence_pct >= 0.80 and wearable_projection.avg_daily_steps >= 8000:
                if base_trend == TrajectoryTrend.DETERIORATING:
                    base_trend = TrajectoryTrend.STABLE
                elif base_trend == TrajectoryTrend.STABLE:
                    base_trend = TrajectoryTrend.IMPROVING
            # If resting heart rate is markedly elevated or adherence very poor
            elif wearable_projection.avg_resting_heart_rate and wearable_projection.avg_resting_heart_rate > 90:
                base_trend = TrajectoryTrend.DETERIORATING

        return base_trend

    def evaluate_observations(
        self,
        observations: List[Observation],
        idrs_score: int = 40,
        age: int = 45,
        gender: str = "MALE",
        smoker: bool = False,
        wearable_projection: Optional[WearableProjection] = None,
    ) -> Tuple[DomainRiskScores, float, RiskTier, TrajectoryTrend, List[RiskDriver], List[ProtectiveFactor]]:
        """Bridge adapter converting raw observations into the legacy tuple format
        for backward compatibility with existing platform components.
        """
        raw_inputs: Dict[str, Any] = {
            "AGE": age,
            "SEX": gender,
            "IDRS_SCORE": idrs_score,
            "SMOKING": smoker,
        }
        for o in observations:
            raw_inputs[o.code] = o.value

        mod_assessment = self.evaluate(raw_inputs, wearable_projection)

        # Map domain scores to legacy DomainRiskScores
        doms = mod_assessment.domain_results
        d_scores = DomainRiskScores(
            diabetes_risk=doms["diabetes"].score or 0.15,
            hypertension_risk=doms["hypertension"].score or 0.12,
            cardiovascular_risk=doms["cardiovascular"].score or 0.10,
            metabolic_syndrome_risk=doms["obesity"].score or 0.15,
            ckd_risk=doms["ckd"].score or 0.08,
            fatty_liver_risk=min(1.0, (doms["obesity"].score or 0.15) * 1.1),
        )

        overall_score = mod_assessment.overall_score if mod_assessment.overall_score is not None else 0.20

        # Map to RiskTier
        if mod_assessment.overall_category == RiskCategory.HIGH:
            overall_tier = RiskTier.CRITICAL if overall_score >= 0.75 else RiskTier.HIGH
        elif mod_assessment.overall_category == RiskCategory.MODERATE:
            overall_tier = RiskTier.MODERATE
        else:
            overall_tier = RiskTier.LOW

        # Convert contributions to legacy RiskDriver and ProtectiveFactor
        legacy_drivers = [
            RiskDriver(
                feature_name=d.feature,
                observed_value=d.observed_value,
                target_value=d.target_value,
                impact_weight=d.impact_weight,
                category=d.category,
                evidence_citation=d.evidence_citation,
            )
            for d in mod_assessment.top_drivers[:5]
        ]

        legacy_protective = [
            ProtectiveFactor(
                feature_name=p.feature,
                observed_value=p.observed_value,
                impact_weight=p.impact_weight,
                category=p.category,
            )
            for p in mod_assessment.protective_factors[:5]
        ]

        return (
            d_scores,
            overall_score,
            overall_tier,
            mod_assessment.trajectory,
            legacy_drivers,
            legacy_protective,
        )


# Global singleton instance
ncd_risk_engine = NCDRiskEngine()
