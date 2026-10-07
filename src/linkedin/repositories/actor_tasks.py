from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from linkedin.core.enums import ActorTaskStatus
from linkedin.db.models.actor_task import ActorTask


def create_actor_task(
    db: Session,
    *,
    job_id: str,
    actor_key: str,
    actor_input_json: dict,
    priority: int = 100,
    status: str = ActorTaskStatus.QUEUED.value,
) -> ActorTask:
    actor_task = ActorTask(
        job_id=job_id,
        actor_key=actor_key,
        actor_input_json=actor_input_json,
        status=status,
        priority=priority,
    )
    db.add(actor_task)
    db.commit()
    db.refresh(actor_task)
    return actor_task


def get_actor_tasks_for_job(db: Session, job_id: str) -> list[ActorTask]:
    statement = (
        select(ActorTask)
        .where(ActorTask.job_id == job_id)
        .order_by(ActorTask.created_at.asc())
    )
    return list(db.scalars(statement))
