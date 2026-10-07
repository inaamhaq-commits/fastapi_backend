from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.core.enums import ActorTaskStatus
from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ActorRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actor_runs"

    actor_task_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("actor_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("chat_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    apify_run_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        default=ActorTaskStatus.QUEUED.value,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    chat_job = relationship("ChatJob", back_populates="actor_runs")
    actor_task = relationship("ActorTask", back_populates="actor_runs")
    raw_documents = relationship("ActorRawDocument", back_populates="actor_run")
    job_postings = relationship("JobPosting", back_populates="actor_run")
