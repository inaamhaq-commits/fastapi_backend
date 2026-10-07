from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AnyUrl, BaseModel, StringConstraints, field_validator


ProfileName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
OptionalProfileText = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=255),
]
ProfileNotes = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=5000),
]


class UserProfileCreateRequest(BaseModel):
    name: ProfileName
    headline: OptionalProfileText = None
    linkedin_url: AnyUrl | None = None
    avatar_url: AnyUrl | None = None
    notes: ProfileNotes = None

    @field_validator("headline", "linkedin_url", "avatar_url", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class UserProfileUpdateRequest(BaseModel):
    name: ProfileName | None = None
    headline: OptionalProfileText = None
    linkedin_url: AnyUrl | None = None
    avatar_url: AnyUrl | None = None
    notes: ProfileNotes = None
    is_active: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def name_cannot_be_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null.")
        return value

    @field_validator("headline", "linkedin_url", "avatar_url", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class UserProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    headline: str | None
    linkedin_url: str | None
    avatar_url: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ManagerUserProfileResponse(UserProfileResponse):
    clients_count: int = 0
