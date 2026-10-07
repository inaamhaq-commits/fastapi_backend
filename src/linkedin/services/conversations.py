from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from linkedin.core.config import settings
from linkedin.core.enums import ConversationSenderType
from linkedin.db.models.ai_suggestion import AiSuggestion
from linkedin.db.models.conversation import Conversation
from linkedin.db.models.conversation_message import ConversationMessage
from linkedin.db.models.user import User
from linkedin.integrations.openai.client import get_openai_client
from linkedin.integrations.openai.embeddings import create_embeddings
from linkedin.integrations.qdrant import search_knowledge_vectors
from linkedin.repositories.conversations import (
    create_ai_suggestion,
    create_conversation,
    create_message,
    finalize_ai_suggestion,
    get_client_for_user,
    get_conversation_for_user,
    get_message_for_conversation,
    get_project_for_user,
    get_suggestion_for_conversation,
    list_conversations_for_user,
    list_recent_messages,
    update_ai_suggestion,
)
from linkedin.schemas.conversations import (
    AiCoachRequest,
    AiSuggestionCreateRequest,
    AiSuggestionFinalizeRequest,
    AiSuggestionUpdateRequest,
    ConversationCreateRequest,
    ConversationMessageCreateRequest,
)


def create_client_conversation(
    db: Session,
    payload: ConversationCreateRequest,
    user: User,
) -> Conversation:
    client = get_client_for_user(db, client_id=str(payload.client_id), user_id=user.id)
    if client is None:
        raise ValueError("Client not found.")

    project = get_project_for_user(db, project_id=str(payload.project_id), user_id=user.id)
    if project is None:
        raise ValueError("Knowledge project not found.")

    return create_conversation(
        db,
        user_id=user.id,
        client_id=str(payload.client_id),
        project_id=str(payload.project_id),
        title=payload.title,
    )


def get_client_conversation(
    db: Session,
    *,
    conversation_id: str,
    user: User,
) -> Conversation | None:
    return get_conversation_for_user(
        db,
        conversation_id=conversation_id,
        user_id=user.id,
    )


def list_client_conversations(
    db: Session,
    *,
    user: User,
    client_id: str | None = None,
) -> list[Conversation]:
    return list_conversations_for_user(db, user_id=user.id, client_id=client_id)


def add_conversation_message(
    db: Session,
    *,
    conversation_id: str,
    payload: ConversationMessageCreateRequest,
    user: User,
) -> ConversationMessage | None:
    conversation = get_client_conversation(db, conversation_id=conversation_id, user=user)
    if conversation is None:
        return None

    return create_message(
        db,
        conversation_id=conversation.id,
        sender_type=payload.sender_type.value,
        message_text=payload.message_text,
    )


def _format_recent_messages(messages: list[ConversationMessage]) -> str:
    return "\n".join(
        f"{message.sender_type}: {message.message_text}" for message in messages
    )


def _format_knowledge_chunks(chunks: list[dict]) -> str:
    if not chunks:
        return "No matching knowledge chunks were found."
    return "\n\n".join(
        (
            f"Source: {chunk.get('source') or 'knowledge base'}\n"
            f"Score: {chunk['score']:.4f}\n"
            f"Text: {chunk.get('text') or ''}"
        )
        for chunk in chunks
    )


def _used_chunk_response(search_results: list[dict]) -> list[dict]:
    used_chunks = []
    for result in search_results:
        payload = result["payload"]
        used_chunks.append(
            {
                "chunk_id": result["chunk_id"],
                "score": result["score"],
                "source": payload.get("filename"),
                "text": payload.get("text"),
            }
        )
    return used_chunks


@dataclass(frozen=True)
class SuggestionContext:
    conversation: Conversation
    latest_message: ConversationMessage
    recent_messages: list[ConversationMessage]
    used_chunks: list[dict]


def _build_suggestion_prompt(context: SuggestionContext) -> str:
    conversation = context.conversation
    latest_message = context.latest_message
    recent_messages = context.recent_messages
    used_chunks = context.used_chunks
    client = conversation.client
    project = conversation.project
    return f"""
You are helping the user write a professional client reply.

Client details:
- Name: {client.name}
- Company: {client.company}
- Notes: {client.notes or "None"}

Knowledge project:
- Name: {project.name}
- Description: {project.description or "None"}

Recent conversation:
{_format_recent_messages(recent_messages)}

Retrieved knowledge:
{_format_knowledge_chunks(used_chunks)}

Latest client message:
{latest_message.message_text}

Write a concise, helpful response the user can send. Do not mention internal
retrieval, embeddings, Qdrant, or the knowledge base. Keep the tone professional
and human.
""".strip()


def _load_suggestion_context(
    db: Session,
    *,
    conversation_id: str,
    payload: AiSuggestionCreateRequest,
    user: User,
) -> SuggestionContext | None:
    conversation = get_client_conversation(db, conversation_id=conversation_id, user=user)
    if conversation is None:
        return None

    message = get_message_for_conversation(
        db,
        conversation_id=conversation.id,
        message_id=str(payload.message_id),
    )
    if message is None:
        return None

    query_vector = create_embeddings([message.message_text])[0]
    search_results = search_knowledge_vectors(
        query_vector=query_vector,
        user_id=user.id,
        project_id=conversation.project_id,
        limit=payload.limit,
    )
    return SuggestionContext(
        conversation=conversation,
        latest_message=message,
        recent_messages=list_recent_messages(db, conversation_id=conversation.id),
        used_chunks=_used_chunk_response(search_results),
    )


def _generate_response_text(*, context: SuggestionContext) -> str:
    response = get_openai_client().responses.create(
        model=settings.openai_model,
        input=_build_suggestion_prompt(context),
    )
    return str(response.output_text).strip()


def generate_ai_suggestion(
    db: Session,
    *,
    conversation_id: str,
    payload: AiSuggestionCreateRequest,
    user: User,
) -> AiSuggestion | None:
    context = _load_suggestion_context(
        db,
        conversation_id=conversation_id,
        payload=payload,
        user=user,
    )
    if context is None:
        return None
    suggested_response = _generate_response_text(context=context)
    return create_ai_suggestion(
        db,
        conversation_id=context.conversation.id,
        source_message_id=context.latest_message.id,
        suggested_response=suggested_response,
        used_chunks=context.used_chunks,
    )


def _stream_text_deltas(prompt: str) -> Generator[str, None, None]:
    with get_openai_client().responses.stream(
        model=settings.openai_model,
        input=prompt,
    ) as stream:
        for event in stream:
            if event.type == "response.output_text.delta":
                yield str(event.delta)
        stream.get_final_response()


def stream_ai_suggestion(
    db: Session,
    *,
    conversation_id: str,
    payload: AiSuggestionCreateRequest,
    user: User,
) -> Generator[dict, None, None]:
    yield {"type": "status", "state": "loading_conversation", "message": "Loading conversation"}
    conversation = get_client_conversation(db, conversation_id=conversation_id, user=user)
    if conversation is None:
        yield {"type": "error", "message": "Conversation or message not found."}
        return

    message = get_message_for_conversation(
        db,
        conversation_id=conversation.id,
        message_id=str(payload.message_id),
    )
    if message is None:
        yield {"type": "error", "message": "Conversation or message not found."}
        return

    yield {"type": "status", "state": "embedding_message", "message": "Understanding message"}
    query_vector = create_embeddings([message.message_text])[0]

    yield {"type": "status", "state": "searching_knowledge", "message": "Searching knowledge"}
    search_results = search_knowledge_vectors(
        query_vector=query_vector,
        user_id=user.id,
        project_id=conversation.project_id,
        limit=payload.limit,
    )
    used_chunks = _used_chunk_response(search_results)

    yield {"type": "status", "state": "loading_history", "message": "Loading conversation history"}
    context = SuggestionContext(
        conversation=conversation,
        latest_message=message,
        recent_messages=list_recent_messages(db, conversation_id=conversation.id),
        used_chunks=used_chunks,
    )

    yield {
        "type": "status",
        "state": "generating_response",
        "message": "Generating response",
        "used_chunks": used_chunks,
    }
    full_response = ""
    for delta in _stream_text_deltas(_build_suggestion_prompt(context)):
        full_response += delta
        yield {"type": "delta", "text": delta}

    yield {"type": "status", "state": "saving_suggestion", "message": "Saving response"}
    suggestion = create_ai_suggestion(
        db,
        conversation_id=context.conversation.id,
        source_message_id=context.latest_message.id,
        suggested_response=full_response.strip(),
        used_chunks=context.used_chunks,
    )
    yield {
        "type": "done",
        "suggestion_id": suggestion.id,
        "suggested_response": suggestion.suggested_response,
        "used_chunks": context.used_chunks,
        "status": suggestion.status,
    }


def edit_ai_suggestion(
    db: Session,
    *,
    conversation_id: str,
    suggestion_id: str,
    payload: AiSuggestionUpdateRequest,
    user: User,
) -> AiSuggestion | None:
    conversation = get_client_conversation(db, conversation_id=conversation_id, user=user)
    if conversation is None:
        return None
    suggestion = get_suggestion_for_conversation(
        db,
        conversation_id=conversation.id,
        suggestion_id=suggestion_id,
    )
    if suggestion is None:
        return None
    return update_ai_suggestion(
        db,
        suggestion=suggestion,
        suggested_response=payload.suggested_response,
    )


def finalize_suggestion(
    db: Session,
    *,
    conversation_id: str,
    suggestion_id: str,
    payload: AiSuggestionFinalizeRequest,
    user: User,
) -> ConversationMessage | None:
    conversation = get_client_conversation(db, conversation_id=conversation_id, user=user)
    if conversation is None:
        return None
    suggestion = get_suggestion_for_conversation(
        db,
        conversation_id=conversation.id,
        suggestion_id=suggestion_id,
    )
    if suggestion is None:
        return None
    return finalize_ai_suggestion(
        db,
        suggestion=suggestion,
        finalized_response=payload.finalized_response,
    )


def ask_ai_coach(
    db: Session,
    *,
    conversation_id: str,
    payload: AiCoachRequest,
    user: User,
) -> str | None:
    conversation = get_client_conversation(db, conversation_id=conversation_id, user=user)
    if conversation is None:
        return None

    recent_messages = list_recent_messages(db, conversation_id=conversation.id)
    prompt = f"""
You are an AI writing coach helping improve a client reply.

Conversation:
{_format_recent_messages(recent_messages)}

Draft response:
{payload.draft_response or "No draft provided."}

User request:
{payload.question}

Return only the improved response or the direct coaching advice. Be short,
specific, and to the point. Do not include intros like "Here is", labels,
explanations, or extra commentary.
""".strip()
    response = get_openai_client().responses.create(
        model=settings.openai_model,
        input=prompt,
    )
    return str(response.output_text).strip()
