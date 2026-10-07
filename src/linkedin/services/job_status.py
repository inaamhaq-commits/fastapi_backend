from __future__ import annotations

from sqlalchemy.orm import Session

from linkedin.core.enums import ActorTaskStatus, JobStatus
from linkedin.db.models.actor_run import ActorRun
from linkedin.db.models.actor_task import ActorTask
from linkedin.db.models.chat_job import ChatJob
from linkedin.repositories.actor_tasks import get_actor_tasks_for_job


def mark_job_running(db: Session, actor_task: ActorTask) -> None:
    chat_job = db.get(ChatJob, actor_task.job_id)
    if chat_job is not None:
        chat_job.status = JobStatus.RUNNING.value


def finalize_job_from_actor_tasks(
    db: Session,
    *,
    actor_task: ActorTask,
    actor_run: ActorRun | None,
    error_message: str | None = None,
) -> None:
    db.flush()
    chat_job = db.get(ChatJob, actor_task.job_id)
    if chat_job is None:
        db.commit()
        return

    actor_tasks = get_actor_tasks_for_job(db, actor_task.job_id)
    statuses = {task.status for task in actor_tasks}

    if ActorTaskStatus.RUNNING.value in statuses or ActorTaskStatus.QUEUED.value in statuses:
        chat_job.status = JobStatus.RUNNING.value
    elif statuses == {ActorTaskStatus.COMPLETED.value}:
        chat_job.status = JobStatus.COMPLETED.value
        chat_job.error = None
    elif statuses == {ActorTaskStatus.FAILED.value}:
        chat_job.status = JobStatus.FAILED.value
        chat_job.error = error_message or (actor_run.error if actor_run is not None else None)
    else:
        chat_job.status = JobStatus.PARTIAL_FAILED.value
        chat_job.error = error_message or (actor_run.error if actor_run is not None else None)

    db.commit()
