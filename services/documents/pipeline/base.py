"""Base interfaces and context for Clinical Document Ingestion Pipeline."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from services.documents.models import DocumentMetadata, DocumentIngestionJob


class PipelineContext(BaseModel):
    """Execution context passed through all 10 stages of document ingestion."""
    metadata: DocumentMetadata
    raw_content: bytes
    job: DocumentIngestionJob
    extracted_text: str = ""
    page_texts: Dict[int, str] = Field(default_factory=dict)
    ocr_lines: list = Field(default_factory=list)
    stage_data: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)



class StageResult(BaseModel):
    """Outcome of a single pipeline stage execution."""
    stage_name: str
    success: bool
    message: str = "Stage completed successfully"
    error: Optional[str] = None
    execution_seconds: float = 0.0


class BasePipelineStage(ABC):
    """Abstract base class for all 10 document ingestion stages."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def process(self, context: PipelineContext) -> StageResult:
        pass
