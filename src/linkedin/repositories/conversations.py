from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from linkedin.core.enums import (
    AiSuggestionStatus,
    ConversationSenderType,
    ConversationStatus,
)
from linkedin.db.models.ai_suggestion import AiSuggestion
from linkedin.db.models.client import Client
from linkedin.db.models.conversation import Conversation
from linkedin.db.models.conversation_message import ConversationMessage
from linkedin.db.models.knowledge_project import KnowledgeProject


def get_client_for_user(db: Session, *, client_id: str, user_id: str) -> Client | None:
    statement = select(Client).where(Client.id == client_id, Client.user_id == user_id)
    return db.scalars(statement).first()


def get_project_for_user(
    db: Session,
    *,
    project_id: str,
    user_id: str,
) -> KnowledgeProject | None:
    statement = select(KnowledgeProject).where(
        KnowledgeProject.id == project_id,
        KnowledgeProject.user_id == user_id,
    )
    return db.scalars(statement).first()


def create_conversation(
    db: Session,
    *,
    user_id: str,
    client_id: str,
    project_id: str,
    title: str,
) -> Conversation:
    conversation = Conversation(
        user_id=user_id,
        client_id=client_id,
        project_id=project_id,
        title=title,
        status=ConversationStatus.ACTIVE.value,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation_for_user(
    db: Session,
    *,
    conversation_id: str,
    user_id: str,
) -> Conversation | None:
    statement = (
        select(Conversation)
        .options(
            selectinload(Conversation.client),
            selectinload(Conversation.project),
            selectinload(Conversation.messages),
            selectinload(Conversation.suggestions),
        )
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    return db.scalars(statement).first()


def list_conversations_for_user(
    db: Session,
    *,
    user_id: str,
    client_id: str | None = None,
) -> list[Conversation]:
    statement = (
        select(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.suggestions))
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    if client_id:
        statement = statement.where(Conversation.client_id == client_id)
    return list(db.scalars(statement).all())


def create_message(
    db: Session,
    *,
    conversation_id: str,
    sender_type: str,
    message_text: str,
) -> ConversationMessage:
    message = ConversationMessage(
        conversation_id=conversation_id,
        sender_type=sender_type,
        message_text=message_text,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_message_for_conversation(
    db: Session,
    *,
    conversation_id: str,
    message_id: str,
) -> ConversationMessage | None:
    statement = select(ConversationMessage).where(
        ConversationMessage.id == message_id,
        ConversationMessage.conversation_id == conversation_id,
    )
    return db.scalars(statement).first()


def list_recent_messages(
    db: Session,
    *,
    conversation_id: str,
    limit: int = 12,
) -> list[ConversationMessage]:
    statement = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    return list(reversed(db.scalars(statement).all()))


def create_ai_suggestion(
    db: Session,
    *,
    conversation_id: str,
    source_message_id: str,
    suggested_response: str,
    used_chunks: list[dict],
) -> AiSuggestion:
    suggestion = AiSuggestion(
        conversation_id=conversation_id,
        source_message_id=source_message_id,
        suggested_response=suggested_response,
        used_chunks=used_chunks,
        status=AiSuggestionStatus.DRAFT.value,
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def get_suggestion_for_conversation(
    db: Session,
    *,
    conversation_id: str,
    suggestion_id: str,
) -> AiSuggestion | None:
    statement = select(AiSuggestion).where(
        AiSuggestion.id == suggestion_id,
        AiSuggestion.conversation_id == conversation_id,
    )
    return db.scalars(statement).first()


def update_ai_suggestion(
    db: Session,
    *,
    suggestion: AiSuggestion,
    suggested_response: str,
) -> AiSuggestion:
    suggestion.suggested_response = suggested_response
    suggestion.status = AiSuggestionStatus.EDITED.value
    db.commit()
    db.refresh(suggestion)
    return suggestion


def finalize_ai_suggestion(
    db: Session,
    *,
    suggestion: AiSuggestion,
    finalized_response: str,
) -> ConversationMessage:
    suggestion.suggested_response = finalized_response
    suggestion.status = AiSuggestionStatus.FINALIZED.value
    message = create_message(
        db,
        conversation_id=suggestion.conversation_id,
        sender_type=ConversationSenderType.FINALIZED.value,
        message_text=finalized_response,
    )
    db.commit()
    db.refresh(suggestion)
    return message
