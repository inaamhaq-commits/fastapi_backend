from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from linkedin.api.deps import get_current_user, get_db
from linkedin.db.models.user import User
from linkedin.schemas.conversations import (
    AiCoachRequest,
    AiCoachResponse,
    AiSuggestionCreateRequest,
    AiSuggestionFinalizeRequest,
    AiSuggestionResponse,
    AiSuggestionUpdateRequest,
    ConversationCreateRequest,
    ConversationCreateResponse,
    ConversationMessageCreateRequest,
    ConversationMessageResponse,
    ConversationResponse,
)
from linkedin.services.conversations import (
    add_conversation_message,
    ask_ai_coach,
    create_client_conversation,
    edit_ai_suggestion,
    finalize_suggestion,
    get_client_conversation,
    list_client_conversations,
    stream_ai_suggestion,
)


router = APIRouter(prefix="/conversations")


@router.post(
    "",
    response_model=ConversationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a client conversation linked to a knowledge project",
)
def create_conversation(
    payload: ConversationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationCreateResponse:
    try:
        conversation = create_client_conversation(db, payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ConversationCreateResponse(
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        project_id=conversation.project_id,
        title=conversation.title,
        status=conversation.status,
    )


@router.get(
    "",
    response_model=list[ConversationResponse],
    summary="List conversations",
)
def list_conversations(
    client_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationResponse]:
    return [
        ConversationResponse.model_validate(conversation)
        for conversation in list_client_conversations(
            db,
            user=current_user,
            client_id=str(client_id) if client_id else None,
        )
    ]


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get a conversation with messages and AI suggestions",
)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    conversation = get_client_conversation(
        db,
        conversation_id=str(conversation_id),
        user=current_user,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ConversationResponse.model_validate(conversation)


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a conversation message",
)
def create_message(
    conversation_id: UUID,
    payload: ConversationMessageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationMessageResponse:
    message = add_conversation_message(
        db,
        conversation_id=str(conversation_id),
        payload=payload,
        user=current_user,
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ConversationMessageResponse.model_validate(message)


@router.post(
    "/{conversation_id}/suggest",
    status_code=status.HTTP_201_CREATED,
    summary="Generate an AI reply suggestion using project knowledge",
)
def create_suggestion(
    conversation_id: UUID,
    payload: AiSuggestionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    def event_stream():
        for event in stream_ai_suggestion(
            db,
            conversation_id=str(conversation_id),
            payload=payload,
            user=current_user,
        ):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.patch(
    "/{conversation_id}/suggestions/{suggestion_id}",
    response_model=AiSuggestionResponse,
    summary="Edit an AI suggestion",
)
def update_suggestion(
    conversation_id: UUID,
    suggestion_id: UUID,
    payload: AiSuggestionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiSuggestionResponse:
    suggestion = edit_ai_suggestion(
        db,
        conversation_id=str(conversation_id),
        suggestion_id=str(suggestion_id),
        payload=payload,
        user=current_user,
    )
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Suggestion not found.")
    return AiSuggestionResponse.model_validate(suggestion)


@router.post(
    "/{conversation_id}/suggestions/{suggestion_id}/finalize",
    response_model=ConversationMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a finalized reply into the conversation",
)
def finalize_ai_reply(
    conversation_id: UUID,
    suggestion_id: UUID,
    payload: AiSuggestionFinalizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationMessageResponse:
    message = finalize_suggestion(
        db,
        conversation_id=str(conversation_id),
        suggestion_id=str(suggestion_id),
        payload=payload,
        user=current_user,
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Suggestion not found.")
    return ConversationMessageResponse.model_validate(message)


@router.post(
    "/{conversation_id}/coach",
    response_model=AiCoachResponse,
    summary="Ask AI Coach for response help",
)
def ask_coach(
    conversation_id: UUID,
    payload: AiCoachRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiCoachResponse:
    coach_response = ask_ai_coach(
        db,
        conversation_id=str(conversation_id),
        payload=payload,
        user=current_user,
    )
    if coach_response is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return AiCoachResponse(coach_response=coach_response)
