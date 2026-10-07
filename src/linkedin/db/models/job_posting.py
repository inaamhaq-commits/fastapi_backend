from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobPosting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_postings"

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
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_page_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_website_domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_site: Mapped[str | None] = mapped_column(Text, nullable=True)

    chat_job = relationship("ChatJob", back_populates="job_postings")
    actor_task = relationship("ActorTask", back_populates="job_postings")
    actor_run = relationship("ActorRun", back_populates="job_postings")
