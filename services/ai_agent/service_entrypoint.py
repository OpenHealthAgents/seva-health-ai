"""Dedicated AI Agent Microservice Entrypoint for SevaHealth AI.

Runs the multi-agent clinical decision intelligence engine,
prevention planner, trajectory explanation agents, and clinical copilot.
"""

from typing import Dict, Any
from fastapi import FastAPI
import uvicorn
import structlog

from packages.config.settings import settings
from services.ai_agent.router import router as ai_router
from agents.router import router as multi_agent_router

logger = structlog.get_logger(__name__)

ai_app = FastAPI(
    title="SevaHealth AI Decision Intelligence Service",
    version=settings.APP_VERSION,
    description="Dedicated Multi-Agent Prevention & Clinical Intelligence Engine",
)

@ai_app.get("/health", tags=["AI Service Health"])
async def ai_service_health() -> Dict[str, Any]:
    return {
        "status": "HEALTHY",
        "service": "sevahealth-ai-service",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "ai_provider": settings.AI_PROVIDER,
        "ai_model": settings.AI_MODEL_NAME,
    }

ai_app.include_router(ai_router, prefix="/api/v1")
ai_app.include_router(multi_agent_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(
        "services.ai_agent.service_entrypoint:ai_app",
        host="0.0.0.0",
        port=8004,
        log_level=settings.LOG_LEVEL.lower(),
    )
