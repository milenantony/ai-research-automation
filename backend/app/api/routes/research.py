from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.research_job import ResearchJob
from app.schemas.research import (
    ResearchJobCreate,
    ResearchJobResponse,
    ResearchJobStatus,
)

router = APIRouter(
    prefix="/research-jobs",
    tags=["Research Jobs"],
)


@router.post(
    "",
    response_model=ResearchJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_research_job(
    request: ResearchJobCreate,
    db: Session = Depends(get_db),
) -> ResearchJob:
    job = ResearchJob(
        topic=request.topic,
        status=ResearchJobStatus.PENDING.value,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


@router.get(
    "/{job_id}",
    response_model=ResearchJobResponse,
)
def get_research_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> ResearchJob:
    job = db.get(ResearchJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research job not found",
        )

    return job
