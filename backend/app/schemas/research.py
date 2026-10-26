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


class ResearchJobResponse(BaseModel):
    id: UUID
    topic: str
    status: ResearchJobStatus
    created_at: datetime