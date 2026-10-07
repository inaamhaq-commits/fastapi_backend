from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.core.enums import KnowledgeChunkStatus
from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_chunks"

    project_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("knowledge_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_file_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("knowledge_project_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qdrant_collection: Mapped[str | None] = mapped_column(Text, nullable=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=KnowledgeChunkStatus.ACTIVE.value,
        server_default=KnowledgeChunkStatus.ACTIVE.value,
    )

    project = relationship("KnowledgeProject", back_populates="chunks")
    project_file = relationship("KnowledgeProjectFile", back_populates="chunks")
