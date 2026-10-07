from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    AnyUrl,
    BaseModel,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from linkedin.core.enums import ClientStatus


ClientText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
OptionalClientText = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=255),
]
NotesText = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=5000),
]
CLIENT_STAGE_FIELDS = (
    "calls_scheduled",
    "qualified",
    "pre_sale",
    "not_a_fit",
)


def _validate_single_client_stage(values: dict[str, object]) -> None:
    selected_stages = [
        field_name for field_name in CLIENT_STAGE_FIELDS if values.get(field_name) is True
    ]
    if len(selected_stages) > 1:
        raise ValueError("Only one client stage can be true at a time.")


class ClientCreateRequest(BaseModel):
    profile_id: UUID | None = None
    name: ClientText
    company: ClientText
    email: EmailStr | None = None
    phone: OptionalClientText = None
    linkedin_url: AnyUrl | None = None
    notes: NotesText = None
    score: int = Field(default=0, ge=0, le=100)
    calls_scheduled: bool = False
    qualified: bool = False
    pre_sale: bool = False
    not_a_fit: bool = False

    @field_validator("email", "phone", "linkedin_url", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def only_one_stage_is_true(self) -> ClientCreateRequest:
        _validate_single_client_stage(self.model_dump())
        return self


class ClientUpdateRequest(BaseModel):
    profile_id: UUID | None = None
    name: ClientText | None = None
    company: ClientText | None = None
    email: EmailStr | None = None
    phone: OptionalClientText = None
    linkedin_url: AnyUrl | None = None
    notes: NotesText = None
    score: int | None = Field(default=None, ge=0, le=100)
    calls_scheduled: bool | None = None
    qualified: bool | None = None
    pre_sale: bool | None = None
    not_a_fit: bool | None = None

    @field_validator("name", "company", mode="before")
    @classmethod
    def required_text_cannot_be_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null.")
        return value

    @field_validator("email", "phone", "linkedin_url", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def only_one_stage_is_true(self) -> ClientUpdateRequest:
        _validate_single_client_stage(self.model_dump(exclude_unset=True))
        return self


class ClientResponse(BaseModel):
    id: UUID
    user_id: UUID
    profile_id: UUID | None
    name: str
    company: str
    email: EmailStr | None
    phone: str | None
    linkedin_url: str | None
    notes: str | None
    score: int = Field(ge=0, le=100)
    calls_scheduled: bool
    qualified: bool
    pre_sale: bool
    not_a_fit: bool
    needs_follow_up: bool
    is_active: bool
    status: ClientStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ManagerUserClientCountResponse(BaseModel):
    user_id: str
    name: str
    email: str
    clients_count: int
