from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class LLMRiskExplanationOutput(BaseModel):
    """Structured LLM output for explaining multi-factor risk (adapted from refactoragent)."""
    plain_summary: str = Field(description="Empathetic, clear non-jargon explanation of overall health trajectory")
    key_drivers: List[str] = Field(description="Top 3-4 specific lifestyle or biomarker factors elevating risk")
    protective_strengths: List[str] = Field(description="1-2 positive factors protecting health")
    recommended_focus_area: str = Field(description="The single most impactful habit to change this month")
    safety_reminder: str = Field(
        default="Clinical review recommended. This is preventive screening, not a medical diagnosis."
    )


class LLMCarePlanOutput(BaseModel):
    """Structured LLM output for 30-day preventive lifestyle medicine interventions."""
    plan_title: str
    focus_domain: str
    nutrition_guidance: str
    activity_guidance: str
    sleep_guidance: str
    stress_guidance: str
    week_1_theme: str
    week_2_theme: str
    week_3_theme: str
    week_4_theme: str
    daily_task_templates: List[Dict[str, Any]] = Field(
        description="Daily actionable micro-habits (pillar, title, description, target_metric)"
    )


class LLMSOAPSummaryOutput(BaseModel):
    """Structured LLM output for Clinician pre-consult triage summary."""
    subjective: str
    objective: str
    assessment: str
    plan: str
    clinical_flags: List[str]
