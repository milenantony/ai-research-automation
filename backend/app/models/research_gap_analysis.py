import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ResearchGapAnalysis(Base):
    __tablename__ = "research_gap_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    selected_paper_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    gaps: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )