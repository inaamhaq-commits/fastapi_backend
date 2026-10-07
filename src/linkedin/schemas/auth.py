from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, StringConstraints

from linkedin.core.enums import UserRole


NameText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
PasswordText = Annotated[
    str,
    StringConstraints(min_length=8, max_length=255),
]


class SignUpRequest(BaseModel):
    full_name: NameText
    email: EmailStr
    password: PasswordText
    role: UserRole = UserRole.USER


class LoginRequest(BaseModel):
    email: EmailStr
    password: PasswordText


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthUserResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuthSuccessResponse(BaseModel):
    user: AuthUserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
