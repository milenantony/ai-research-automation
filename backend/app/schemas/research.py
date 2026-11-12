from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ResearchJobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ResearchJobCreate(BaseModel):
    topic: str = Field(
        min_length=5,
        max_length=500,
        description="The academic research topic",
    )
class ResearchJobUpdate(BaseModel):
    topic: str = Field(
        min_length=5,
        max_length=500,
        description="The updated academic research topic",
    )

class ResearchJobResponse(BaseModel):
    id: UUID
    topic: str
    status: ResearchJobStatus
    created_at: datetime

class ResearchSummaryRequest(BaseModel):
    research_context: str = Field(
        min_length=1,
        description="Research material used to generate the summary",
    )


class ResearchSummaryResponse(BaseModel):
    job_id: UUID
    topic: str
    summary: str
