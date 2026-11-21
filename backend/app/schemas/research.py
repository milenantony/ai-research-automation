from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

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

class PaperSearchRequest(BaseModel):
    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of papers to retrieve from each provider",
    )
    refine_query: bool = Field(
        default=False,
        description="Use the Paper Discovery Agent to refine the job topic before searching",
    )
class LinkedPaperSummaryRequest(BaseModel):
    paper_ids: list[UUID] = Field(
        min_length=1,
        description="Linked paper IDs to summarize, in the requested order",
    )

class GapAnalysisRequest(BaseModel):
    paper_ids: list[UUID] = Field(
        min_length=1,
        description="Human-selected linked paper IDs, in evidence order",
    )



class ResearchGap(BaseModel):
    category: Literal["author_reported_limitation", "inferred_gap"]
    description: str
    supporting_paper_ids: list[UUID] = Field(min_length=1)
    evidence: str
    review_status: Literal["pending", "approved", "rejected"] = "pending"

class GapAnalysisResponse(BaseModel):
    job_id: UUID
    topic: str
    gaps: list[ResearchGap]

class SavedGapAnalysisResponse(GapAnalysisResponse):
    id: UUID
    selected_paper_ids: list[UUID]
    created_at: datetime
class GapReviewRequest(BaseModel):
    gap_index: int = Field(ge=0, description="Zero-based position in the saved gaps")
    review_status: Literal["approved", "rejected"]

class ResearchPaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    source: str
    title: str
    abstract: str | None
    authors: list[str]
    published_date: datetime | None
    paper_url: str | None
    pdf_url: str | None
    doi: str | None
    created_at: datetime