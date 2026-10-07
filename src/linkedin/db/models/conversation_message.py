from __future__ import annotations

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConversationMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversation_messages"

    conversation_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
    suggestions = relationship(
        "AiSuggestion",
        back_populates="source_message",
        cascade="all, delete-orphan",
    )
