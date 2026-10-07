from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from linkedin.api.deps import get_db
from linkedin.schemas.chat import (
    ActorRawDocumentResponse,
    ChatJobDetailResponse,
    ChatJobResponse,
    ChatRequest,
    JobPostingResponse,
)
from linkedin.services.chat import (
    create_chat_job,
    get_all_chat_results,
    get_chat_job_detail,
    get_chat_job_raw_documents,
    get_chat_job_results,
)


router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a chat job",
)
def create_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatJobResponse:
    return create_chat_job(db, payload)


@router.get(
    "/jobs/{job_id}",
    response_model=ChatJobDetailResponse,
    summary="Get chat job status",
)
def get_chat_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> ChatJobDetailResponse:
    chat_job = get_chat_job_detail(db, str(job_id))
    if chat_job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return chat_job


@router.get(
    "/all",
    response_model=list[JobPostingResponse],
    summary="Get all normalized job postings",
)
def get_all_results(
    db: Session = Depends(get_db),
) -> list[JobPostingResponse]:
    return get_all_chat_results(db)


@router.get(
    "/jobs/{job_id}/results",
    response_model=list[JobPostingResponse],
    summary="Get normalized job postings for a chat job",
)
def get_chat_results(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> list[JobPostingResponse]:
    return get_chat_job_results(db, str(job_id))


@router.get(
    "/jobs/{job_id}/raw-documents",
    response_model=list[ActorRawDocumentResponse],
    summary="Get raw actor documents for a chat job",
)
def get_chat_raw_documents(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> list[ActorRawDocumentResponse]:
    return get_chat_job_raw_documents(db, str(job_id))
