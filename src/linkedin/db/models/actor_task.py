from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.core.enums import ActorTaskStatus
from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ActorTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actor_tasks"

    job_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("chat_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    actor_input_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        default=ActorTaskStatus.QUEUED.value,
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    chat_job = relationship("ChatJob", back_populates="actor_tasks")
    actor_runs = relationship("ActorRun", back_populates="actor_task")
    raw_documents = relationship("ActorRawDocument", back_populates="actor_task")
    job_postings = relationship("JobPosting", back_populates="actor_task")
