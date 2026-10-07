from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from linkedin.core.enums import (
    AiSuggestionStatus,
    ConversationSenderType,
    ConversationStatus,
)


ConversationTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
MessageText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=8000),
]
CoachQuestion = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]


class ConversationCreateRequest(BaseModel):
    client_id: UUID
    project_id: UUID
    title: ConversationTitle


class ConversationMessageCreateRequest(BaseModel):
    sender_type: ConversationSenderType
    message_text: MessageText


class AiSuggestionCreateRequest(BaseModel):
    message_id: UUID
    limit: int = Field(default=5, ge=1, le=10)


class AiSuggestionUpdateRequest(BaseModel):
    suggested_response: MessageText


class AiSuggestionFinalizeRequest(BaseModel):
    finalized_response: MessageText


class AiCoachRequest(BaseModel):
    question: CoachQuestion
    draft_response: MessageText | None = None


class UsedChunkResponse(BaseModel):
    chunk_id: str
    score: float
    source: str | None = None
    text: str | None = None


class ConversationMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_type: ConversationSenderType | str
    message_text: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AiSuggestionResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    source_message_id: UUID
    suggested_response: str
    used_chunks: list[UsedChunkResponse] | list[dict]
    status: AiSuggestionStatus | str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    client_id: UUID
    project_id: UUID
    title: str
    status: ConversationStatus | str
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse] = []
    suggestions: list[AiSuggestionResponse] = []

    model_config = {"from_attributes": True}


class ConversationCreateResponse(BaseModel):
    conversation_id: UUID
    client_id: UUID
    project_id: UUID
    title: str
    status: ConversationStatus | str


class AiCoachResponse(BaseModel):
    coach_response: str
