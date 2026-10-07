from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ActorRawDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actor_raw_documents"

    job_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("chat_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_task_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("actor_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_run_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("actor_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_actor_key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload_jsonb: Mapped[dict] = mapped_column(JSON, nullable=False)

    chat_job = relationship("ChatJob", back_populates="raw_documents")
    actor_task = relationship("ActorTask", back_populates="raw_documents")
    actor_run = relationship("ActorRun", back_populates="raw_documents")
