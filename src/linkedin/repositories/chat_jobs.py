from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from linkedin.db.models.chat_job import ChatJob


def create_chat_job(
    db: Session,
    *,
    user_message: str,
    normalized_query: str | None = None,
    status: str | None = None,
) -> ChatJob:
    chat_job = ChatJob(
        user_message=user_message,
        normalized_query=normalized_query,
        status=status or ChatJob.status.default.arg,
    )
    db.add(chat_job)
    db.commit()
    db.refresh(chat_job)
    return chat_job


def get_chat_job(db: Session, job_id: str) -> ChatJob | None:
    statement = (
        select(ChatJob)
        .where(ChatJob.id == job_id)
        .options(
            selectinload(ChatJob.actor_tasks),
            selectinload(ChatJob.actor_runs),
        )
    )
    return db.scalar(statement)
