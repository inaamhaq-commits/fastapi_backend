from sqlalchemy.orm import Session

from linkedin.core.enums import ActorTaskStatus, JobStatus
from linkedin.integrations.openai.planner import generate_actor_tasks
from linkedin.repositories.actor_tasks import create_actor_task as create_actor_task_record
from linkedin.repositories.actor_raw_documents import get_raw_documents_for_job
from linkedin.repositories.chat_jobs import (
    create_chat_job as create_chat_job_record,
    get_chat_job,
)
from linkedin.repositories.job_postings import get_all_job_postings, get_job_postings_for_job
from linkedin.schemas.chat import (
    ActorRawDocumentResponse,
    ChatJobDetailResponse,
    ChatJobResponse,
    ChatRequest,
    JobPostingResponse,
)


def create_chat_job(db: Session, payload: ChatRequest) -> ChatJobResponse:
    chat_job = create_chat_job_record(
        db,
        user_message=payload.message,
        normalized_query=None,
        status=JobStatus.PLANNING.value,
    )

    actor_tasks = []
    try:
        planned_tasks = generate_actor_tasks(payload.message)
        primary_task = planned_tasks[0]

        chat_job.normalized_query = primary_task.normalized_query
        chat_job.status = JobStatus.QUEUED.value
        db.commit()
        db.refresh(chat_job)

        for planned_task in planned_tasks:
            actor_task = create_actor_task_record(
                db,
                job_id=chat_job.id,
                actor_key=planned_task.actor_key,
                actor_input_json=planned_task.actor_input,
            )
            actor_tasks.append(actor_task)
            # Redis queueing is disabled for the low-user deployment.
            # Actor task records remain queued in the database.
    except Exception as exc:
        chat_job.status = JobStatus.FAILED.value
        chat_job.error = str(exc)
        for actor_task in actor_tasks:
            actor_task.status = ActorTaskStatus.FAILED.value
        db.commit()
        raise

    return ChatJobResponse(job_id=chat_job.id, status=chat_job.status)


def get_chat_job_detail(db: Session, job_id: str) -> ChatJobDetailResponse | None:
    chat_job = get_chat_job(db, job_id)
    if chat_job is None:
        return None
    return ChatJobDetailResponse.model_validate(chat_job)


def get_chat_job_results(db: Session, job_id: str) -> list[JobPostingResponse]:
    postings = get_job_postings_for_job(db, job_id)
    return [JobPostingResponse.model_validate(posting) for posting in postings]


def get_all_chat_results(db: Session) -> list[JobPostingResponse]:
    postings = get_all_job_postings(db)
    return [JobPostingResponse.model_validate(posting) for posting in postings]


def get_chat_job_raw_documents(
    db: Session,
    job_id: str,
) -> list[ActorRawDocumentResponse]:
    documents = get_raw_documents_for_job(db, job_id)
    return [
        ActorRawDocumentResponse.model_validate(document)
        for document in documents
    ]
