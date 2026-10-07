from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from urllib.parse import urlparse
from typing import Any

from sqlalchemy.orm import Session

from linkedin.cache.redis import get_redis_client
from linkedin.core.config import settings
from linkedin.core.enums import ActorTaskStatus, JobStatus
from linkedin.db.models.actor_raw_document import ActorRawDocument
from linkedin.db.models.actor_run import ActorRun
from linkedin.db.models.actor_task import ActorTask
from linkedin.db.models.chat_job import ChatJob
from linkedin.db.models.job_posting import JobPosting
from linkedin.db.session import create_database_tables, get_session_factory
from linkedin.services.job_status import finalize_job_from_actor_tasks, mark_job_running

logger = logging.getLogger(__name__)

try:
    from apify_client import ApifyClient
except ImportError:
    ApifyClient = None

try:
    from redis.exceptions import TimeoutError as RedisTimeoutError
except ImportError:
    RedisTimeoutError = TimeoutError


@dataclass(slots=True)
class GlassdoorTaskMessage:
    actor_task_id: str
    actor_key: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "GlassdoorTaskMessage":
        return cls(
            actor_task_id=str(payload["actor_task_id"]),
            actor_key=str(payload["actor_key"]),
        )


def get_apify_client() -> Any:
    if ApifyClient is None:
        raise RuntimeError(
            "apify-client is not installed. Run `uv sync` to install worker dependencies."
        )
    if not settings.apify_api_token:
        raise RuntimeError("APIFY_API_TOKEN is not configured.")
    return ApifyClient(settings.apify_api_token)


def pop_queue_message(block_seconds: int = 5) -> GlassdoorTaskMessage | None:
    redis_client = get_redis_client()
    try:
        item = redis_client.blpop(
            settings.glassdoor_queue_name,
            timeout=block_seconds,
        )
    except RedisTimeoutError:
        logger.debug(
            "No Glassdoor task received from Redis queue '%s' within %s seconds.",
            settings.glassdoor_queue_name,
            block_seconds,
        )
        return None

    if item is None:
        return None

    _, raw_message = item
    payload = json.loads(raw_message)
    return GlassdoorTaskMessage.from_payload(payload)


def get_actor_task(db: Session, actor_task_id: str) -> ActorTask | None:
    return db.get(ActorTask, actor_task_id)


def start_actor_run(db: Session, actor_task: ActorTask) -> ActorRun:
    actor_task.status = ActorTaskStatus.RUNNING.value
    actor_task.attempt_count += 1

    mark_job_running(db, actor_task)

    actor_run = ActorRun(
        actor_task_id=actor_task.id,
        job_id=actor_task.job_id,
        actor_key=actor_task.actor_key,
        status=ActorTaskStatus.RUNNING.value,
        started_at=datetime.now(UTC),
    )
    db.add(actor_run)
    db.commit()
    db.refresh(actor_run)
    return actor_run


def finalize_success(db: Session, actor_task: ActorTask, actor_run: ActorRun) -> None:
    actor_task.status = ActorTaskStatus.COMPLETED.value
    actor_run.status = ActorTaskStatus.COMPLETED.value
    actor_run.finished_at = datetime.now(UTC)
    finalize_job_from_actor_tasks(db, actor_task=actor_task, actor_run=actor_run)


def finalize_failure(
    db: Session,
    actor_task: ActorTask,
    actor_run: ActorRun | None,
    error_message: str,
) -> None:
    actor_task.status = ActorTaskStatus.FAILED.value

    if actor_run is not None:
        actor_run.status = ActorTaskStatus.FAILED.value
        actor_run.error = error_message
        actor_run.finished_at = datetime.now(UTC)
    finalize_job_from_actor_tasks(
        db,
        actor_task=actor_task,
        actor_run=actor_run,
        error_message=error_message,
    )


def build_run_input(actor_task: ActorTask) -> dict[str, Any]:
    if not isinstance(actor_task.actor_input_json, dict):
        raise RuntimeError("actor_input_json must be a JSON object.")
    return dict(actor_task.actor_input_json)


def fetch_actor_items(actor_task: ActorTask) -> tuple[str, list[dict[str, Any]]]:
    client = get_apify_client()
    run_input = build_run_input(actor_task)

    run = client.actor(settings.glassdoor_actor_id).call(run_input=run_input)
    dataset_id = getattr(run, "default_dataset_id", None)
    run_id = getattr(run, "id", None)

    if dataset_id is None and isinstance(run, dict):
        dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
        run_id = run.get("id", run_id)

    if dataset_id is None:
        raise RuntimeError("Apify run did not include a default dataset ID.")

    items = list(client.dataset(dataset_id).iterate_items())
    return str(run_id or dataset_id), items


def map_posting_fields(item: dict[str, Any]) -> dict[str, Any]:
    def normalize_domain(url: str | None) -> str | None:
        if not url:
            return None
        try:
            hostname = urlparse(url).hostname
        except ValueError:
            return None
        return hostname.lower() if hostname else None

    company_name = item.get("companyName") or item.get("employerName")
    title = item.get("title") or item.get("jobTitle") or "Untitled job"
    description = item.get("description") or item.get("jobDescription")
    job_type = item.get("employmentType") or item.get("jobType")
    location = item.get("locationName") or item.get("location")
    job_url = item.get("jobUrl") or item.get("url")
    company_page_url = item.get("companyUrl") or item.get("companyPageUrl")
    company_website_url = (
        item.get("companyWebsite")
        or item.get("companyWebsiteUrl")
        or item.get("employerWebsite")
        or item.get("website")
    )
    linkedin_url = item.get("linkedInUrl") or item.get("linkedinUrl")
    external_id = item.get("jobId") or item.get("id")
    source_url = item.get("url")

    return {
        "external_id": str(external_id) if external_id is not None else None,
        "title": str(title),
        "company_name": str(company_name) if company_name else None,
        "description": str(description) if description else None,
        "job_type": str(job_type) if job_type else None,
        "location": str(location) if location else None,
        "job_url": str(job_url) if job_url else None,
        "company_page_url": str(company_page_url) if company_page_url else None,
        "company_website_url": (
            str(company_website_url) if company_website_url else None
        ),
        "company_website_domain": normalize_domain(
            str(company_website_url) if company_website_url else None
        ),
        "linkedin_url": str(linkedin_url) if linkedin_url else None,
        "source_url": str(source_url) if source_url else None,
    }


def store_items(
    db: Session,
    *,
    actor_task: ActorTask,
    actor_run: ActorRun,
    items: list[dict[str, Any]],
) -> None:
    for item in items:
        mapped = map_posting_fields(item)

        raw_document = ActorRawDocument(
            job_id=actor_task.job_id,
            actor_task_id=actor_task.id,
            actor_run_id=actor_run.id,
            source_actor_key=actor_task.actor_key,
            external_id=mapped["external_id"],
            source_url=mapped["source_url"],
            raw_payload_jsonb=item,
        )
        db.add(raw_document)

        posting = JobPosting(
            job_id=actor_task.job_id,
            actor_task_id=actor_task.id,
            actor_run_id=actor_run.id,
            source_actor_key=actor_task.actor_key,
            external_id=mapped["external_id"],
            title=mapped["title"],
            company_name=mapped["company_name"],
            description=mapped["description"],
            job_type=mapped["job_type"],
            location=mapped["location"],
            job_url=mapped["job_url"],
            company_page_url=mapped["company_page_url"],
            company_website_url=mapped["company_website_url"],
            company_website_domain=mapped["company_website_domain"],
            linkedin_url=mapped["linkedin_url"],
            source_site=settings.glassdoor_source_site,
        )
        db.add(posting)

    db.commit()


def process_actor_task(actor_task_id: str) -> None:
    session_factory = get_session_factory()

    with session_factory() as db:
        actor_task = get_actor_task(db, actor_task_id)
        if actor_task is None:
            logger.warning("Actor task %s was not found.", actor_task_id)
            return
        if actor_task.status != ActorTaskStatus.QUEUED.value:
            logger.info(
                "Skipping Glassdoor task %s with status=%s",
                actor_task_id,
                actor_task.status,
            )
            return

        actor_run: ActorRun | None = None
        try:
            actor_run = start_actor_run(db, actor_task)
            apify_run_id, items = fetch_actor_items(actor_task)
            actor_run.apify_run_id = apify_run_id
            db.commit()

            store_items(
                db,
                actor_task=actor_task,
                actor_run=actor_run,
                items=items,
            )
            finalize_success(db, actor_task, actor_run)
        except Exception as exc:
            logger.exception("Glassdoor worker failed for actor task %s", actor_task_id)
            db.rollback()
            finalize_failure(db, actor_task, actor_run, str(exc))


def run_forever() -> None:
    create_database_tables()
    logger.info(
        "Glassdoor worker listening on Redis queue '%s'",
        settings.glassdoor_queue_name,
    )

    while True:
        message = pop_queue_message()
        if message is None:
            continue

        if message.actor_key != "glassdoor_jobs":
            logger.info(
                "Skipping non-Glassdoor task %s with actor_key=%s",
                message.actor_task_id,
                message.actor_key,
            )
            continue

        process_actor_task(message.actor_task_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
