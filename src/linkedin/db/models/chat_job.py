from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from linkedin.core.enums import JobStatus
from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChatJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_jobs"

    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        default=JobStatus.QUEUED.value,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_tasks = relationship("ActorTask", back_populates="chat_job")
    actor_runs = relationship("ActorRun", back_populates="chat_job")
    raw_documents = relationship("ActorRawDocument", back_populates="chat_job")
    job_postings = relationship("JobPosting", back_populates="chat_job")
