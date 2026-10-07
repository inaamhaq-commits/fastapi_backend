from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from linkedin.db.models.job_posting import JobPosting


def get_job_postings_for_job(db: Session, job_id: str) -> list[JobPosting]:
    statement = (
        select(JobPosting)
        .where(JobPosting.job_id == job_id)
        .order_by(JobPosting.created_at.asc())
    )
    return list(db.scalars(statement))


def get_all_job_postings(db: Session) -> list[JobPosting]:
    statement = select(JobPosting).order_by(JobPosting.created_at.desc())
    return list(db.scalars(statement))
