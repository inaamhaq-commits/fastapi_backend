from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.core.enums import ClientStatus
from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Client(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clients"

    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    calls_scheduled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    qualified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    pre_sale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    not_a_fit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    needs_follow_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    status: Mapped[str] = mapped_column(Text, nullable=False, default=ClientStatus.NEW.value, server_default=ClientStatus.NEW.value)

    user = relationship("User", back_populates="clients")
    profile = relationship("UserProfile", back_populates="clients")
    conversations = relationship("Conversation", back_populates="client")
