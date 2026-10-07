from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from linkedin.core.enums import AiSuggestionStatus
from linkedin.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AiSuggestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_suggestions"

    conversation_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_message_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("conversation_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suggested_response: Mapped[str] = mapped_column(Text, nullable=False)
    used_chunks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=AiSuggestionStatus.DRAFT.value,
        server_default=AiSuggestionStatus.DRAFT.value,
    )

    conversation = relationship("Conversation", back_populates="suggestions")
    source_message = relationship(
        "ConversationMessage",
        back_populates="suggestions",
    )
