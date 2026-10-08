"""REST API Router for SevaHealth Bounded Multi-Agent System."""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
import structlog

from packages.types.enums import UserRole
from packages.auth.jwt import get_current_user_token, TokenPayload
from agents.registry import agent_registry
from agents.core.models import AgentMetadata, BoundedAgentResult
from agents.core.base import AgentAuthorizationError, AgentExecutionTimeoutError
from agents.core.telemetry import agent_telemetry_buffer
from agents.orchestrator import orchestrator, ScreeningPipelineResult

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["Bounded Multi-Agent System"])


class ExecuteAgentRequest(BaseModel):
    citizen_id: Optional[str] = None
    input_payload: Dict[str, Any]


class ConversationalSafetyCheckRequest(BaseModel):
    citizen_id: str
    message: str
    vitals: Dict[str, float] = Field(default_factory=dict)


class ScreeningPipelineRequest(BaseModel):
    citizen_id: str
    age: int = 45
    gender: str = "MALE"
    waist_cm: float = 94.0
    activity_level: str = "Sedentary"
    family_history: str = "One parent"
    cbac_answers: Dict[str, Any] = Field(default_factory=dict)
    vitals: Dict[str, float] = Field(default_factory=dict)


@router.get("", summary="List all 9 bounded agents and contract specifications")
async def list_agents():
    """Returns metadata, allowed tools, safety constraints, schemas, and status for all agents."""
    return agent_registry.get_system_health()


@router.get("/specs", response_model=List[AgentMetadata], summary="Get full agent contract specifications")
async def get_agent_specs():
    return agent_registry.list_agents()


@router.get("/{agent_name}", response_model=AgentMetadata, summary="Get metadata for a specific agent")
async def get_agent_detail(agent_name: str):
    try:
        agent = agent_registry.get_agent(agent_name)
        return agent.get_metadata()
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{agent_name}/execute", summary="Execute a bounded agent with authorization and retry enforcement")
async def execute_agent(
    agent_name: str,
    payload: ExecuteAgentRequest,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    try:
        result = await agent_registry.execute_agent(
            name=agent_name,
            input_payload=payload.input_payload,
            actor=current_user,
            citizen_id=payload.citizen_id,
        )
        return result
    except AgentAuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/orchestrate/screening-pipeline", response_model=ScreeningPipelineResult, summary="Run multi-agent screening-to-prevention pipeline")
async def run_screening_pipeline(
    payload: ScreeningPipelineRequest,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    try:
        return await orchestrator.run_screening_to_prevention_pipeline(
            citizen_id=payload.citizen_id,
            age=payload.age,
            gender=payload.gender,
            waist_cm=payload.waist_cm,
            activity_level=payload.activity_level,
            family_history=payload.family_history,
            cbac_answers=payload.cbac_answers,
            vitals=payload.vitals,
            actor=current_user,
        )
    except AgentAuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/orchestrate/conversational-check", summary="Run emergency check + education routing pipeline")
async def run_conversational_check(
    payload: ConversationalSafetyCheckRequest,
    current_user: TokenPayload = Depends(get_current_user_token),
):
    try:
        return await orchestrator.run_conversational_safety_pipeline(
            citizen_id=payload.citizen_id,
            user_message=payload.message,
            actor=current_user,
            vitals=payload.vitals,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/telemetry/logs", summary="Get multi-agent forensic execution audit logs")
async def get_agent_telemetry_logs(
    agent_name: Optional[str] = Query(None),
    citizen_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: TokenPayload = Depends(get_current_user_token),
):
    return agent_telemetry_buffer.get_logs(
        agent_name=agent_name,
        citizen_id=citizen_id,
        limit=limit,
    )
