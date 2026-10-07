from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


ProjectName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]
ProjectDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]
Filename = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
ContentType = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]


class ProjectFileCreateRequest(BaseModel):
    filename: Filename
    content_type: ContentType
    file_size: int | None = Field(default=None, ge=0)


class ProjectCreateRequest(BaseModel):
    name: ProjectName
    description: ProjectDescription | None = None
    files: list[ProjectFileCreateRequest] = Field(min_length=1, max_length=25)


class ProjectFileUploadResponse(BaseModel):
    project_file_id: UUID
    filename: str
    label: str
    bucket: str
    object_key: str
    upload_url: str
    expires_in: int


class ProjectCreateResponse(BaseModel):
    project_id: UUID
    status: Literal["uploading"]
    uploads: list[ProjectFileUploadResponse]


class ProjectFileResponse(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    label: str
    content_type: str
    file_size: int | None
    bucket: str
    object_key: str
    upload_status: str
    processing_status: str
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime
    files: list[ProjectFileResponse]

    model_config = {"from_attributes": True}


class ProjectCompleteResponse(BaseModel):
    project_id: UUID
    status: str
    files: list[ProjectFileResponse]
