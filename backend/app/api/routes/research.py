
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.research_job import ResearchJob
from app.schemas.research import (
    ResearchJobCreate,
    ResearchJobResponse,
    ResearchJobStatus,
)

logger = logging.getLogger(__name__)

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

    try:
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(
            "Research job created successfully: %s",
            job.id,
        )

    except SQLAlchemyError:
        db.rollback()

        logger.exception("Failed to create research job")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create research job",
        )

    return job


@router.get(
    "/{job_id}",
    response_model=ResearchJobResponse,
)
def get_research_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> ResearchJob:

    try:
        job = db.get(ResearchJob, job_id)

    except SQLAlchemyError:
        db.rollback()

        logger.exception("Failed to retrieve research job")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve research job",
        )

    if job is None:
        logger.warning(
            "Research job not found: %s",
            job_id,
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research job not found",
        )

    logger.info(
        "Research job retrieved successfully: %s",
        job.id,
    )

    return job
