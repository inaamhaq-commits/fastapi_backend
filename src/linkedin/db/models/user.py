from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from linkedin.core.enums import UserRole
from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=UserRole.USER.value,
        server_default=UserRole.USER.value,
    )

    clients = relationship("Client", back_populates="user")
    profiles = relationship("UserProfile", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    knowledge_projects = relationship("KnowledgeProject", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
