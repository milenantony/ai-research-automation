from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.schemas.research import (
    ResearchJobCreate,
    ResearchJobResponse,
    ResearchJobStatus,
)

router = APIRouter(
    prefix="/research-jobs",
    tags=["Research Jobs"],
)

# Temporary storage; PostgreSQL will replace this.
research_jobs: dict[str, ResearchJobResponse] = {}


@router.post(
    "",
    response_model=ResearchJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_research_job(
request: ResearchJobCreate,) -> ResearchJobResponse:

    job = ResearchJobResponse(
        id=uuid4(),
        topic=request.topic,
        status=ResearchJobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )

    research_jobs[str(job.id)] = job

    return job


@router.get(
    "/{job_id}",
    response_model=ResearchJobResponse,
)
def get_research_job(job_id: str) -> ResearchJobResponse:

    job = research_jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research job not found",
        )

    return job