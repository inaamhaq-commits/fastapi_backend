from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from linkedin.db.models.actor_raw_document import ActorRawDocument


def get_raw_documents_for_job(db: Session, job_id: str) -> list[ActorRawDocument]:
    statement = (
        select(ActorRawDocument)
        .where(ActorRawDocument.job_id == job_id)
        .order_by(ActorRawDocument.created_at.asc())
    )
    return list(db.scalars(statement))
