from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.core.enums import (
    KnowledgeFileProcessingStatus,
    KnowledgeFileUploadStatus,
)
from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeProjectFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_project_files"

    project_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("knowledge_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bucket: Mapped[str] = mapped_column(Text, nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    upload_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=KnowledgeFileUploadStatus.PENDING.value,
        server_default=KnowledgeFileUploadStatus.PENDING.value,
    )
    processing_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=KnowledgeFileProcessingStatus.QUEUED.value,
        server_default=KnowledgeFileProcessingStatus.QUEUED.value,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    project = relationship("KnowledgeProject", back_populates="files")
    chunks = relationship(
        "KnowledgeChunk",
        back_populates="project_file",
        cascade="all, delete-orphan",
    )
