from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

from packages.types.enums import RiskTier, TrajectoryTrend


class DomainRiskScores(BaseModel):
    diabetes_risk: float              # 0.0 to 1.0 (Prediabetes / T2DM probability)
    hypertension_risk: float          # 0.0 to 1.0 (Prehypertension / Stage 1 / Stage 2)
    cardiovascular_risk: float        # 0.0 to 1.0 (10-year ASCVD composite)
    metabolic_syndrome_risk: float    # 0.0 to 1.0 (Central adiposity + dyslipidemia)
    ckd_risk: float                   # 0.0 to 1.0 (Renal function markers)
    fatty_liver_risk: float           # 0.0 to 1.0 (MASLD / NAFLD FIB-4 surrogate)


class RiskDriver(BaseModel):
    """Explainable feature driver (+% risk contribution)."""
    feature_name: str
    observed_value: str
    target_value: str
    impact_weight: float              # e.g. +0.24 (+24%)
    category: str = "BIOMETRIC"       # "BIOMETRIC", "LIFESTYLE", "GENETIC"
    evidence_citation: str = "ICMR Guidelines / Clinical Evidence"


class ProtectiveFactor(BaseModel):
    """Explainable protective factor (-% risk reduction)."""
    feature_name: str
    observed_value: str
    impact_weight: float              # e.g. -0.10 (-10%)
    category: str = "LIFESTYLE"


class RiskAssessment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    citizen_id: str
    screening_session_id: Optional[str] = None
    overall_score: float              # 0.0 to 1.0 (0-100% composite index)
    overall_tier: RiskTier
    domains: DomainRiskScores
    trajectory: TrajectoryTrend
    confidence_score: float           # 0.0 to 1.0 (completeness of lab/biometric data)
    top_drivers: List[RiskDriver] = []
    protective_factors: List[ProtectiveFactor] = []
    clinical_summary: str
    safety_disclaimer: str = (
        "CLINICAL REVIEW RECOMMENDED: This assessment is an AI-assisted preventive health screening "
        "tool based on population guidelines. It does NOT constitute a medical diagnosis or treatment plan."
    )
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
