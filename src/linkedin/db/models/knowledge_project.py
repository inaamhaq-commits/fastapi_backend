from __future__ import annotations

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.core.enums import KnowledgeProjectStatus
from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeProject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_projects"

    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=KnowledgeProjectStatus.UPLOADING.value,
        server_default=KnowledgeProjectStatus.UPLOADING.value,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="knowledge_projects")
    files = relationship(
        "KnowledgeProjectFile",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    chunks = relationship(
        "KnowledgeChunk",
        back_populates="project",
        cascade="all, delete-orphan",
    )
