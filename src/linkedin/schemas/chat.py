from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from linkedin.core.enums import ActorTaskStatus, JobStatus


MessageText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]


class ChatRequest(BaseModel):
    message: MessageText


class ChatJobResponse(BaseModel):
    job_id: UUID
    status: Literal["queued"] = "queued"


class ActorTaskSummary(BaseModel):
    id: UUID
    actor_key: str
    status: ActorTaskStatus | str
    priority: int
    attempt_count: int

    model_config = {"from_attributes": True}


class ActorRunSummary(BaseModel):
    id: UUID
    actor_task_id: UUID
    actor_key: str
    apify_run_id: str | None
    status: ActorTaskStatus | str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None

    model_config = {"from_attributes": True}


class ChatJobDetailResponse(BaseModel):
    id: UUID
    user_message: str
    normalized_query: str | None
    status: JobStatus | str
    created_at: datetime
    updated_at: datetime
    error: str | None
    actor_tasks: list[ActorTaskSummary]
    actor_runs: list[ActorRunSummary]

    model_config = {"from_attributes": True}


class JobPostingResponse(BaseModel):
    id: UUID
    job_id: UUID
    actor_task_id: UUID
    actor_run_id: UUID
    source_actor_key: str
    external_id: str | None
    title: str
    company_name: str | None
    description: str | None
    job_type: str | None
    location: str | None
    job_url: str | None
    company_page_url: str | None
    company_website_url: str | None
    company_website_domain: str | None
    linkedin_url: str | None
    posted_at: datetime | None
    source_site: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActorRawDocumentResponse(BaseModel):
    id: UUID
    job_id: UUID
    actor_task_id: UUID
    actor_run_id: UUID
    source_actor_key: str
    external_id: str | None
    source_url: str | None
    raw_payload_jsonb: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
