from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import (
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
)
from redis import Redis

from linkedin.cache.redis import get_redis_client
from linkedin.core.config import settings
from linkedin.db.session import get_session_factory
from linkedin.services.knowledge_ingestion import (
    PermanentIngestionError,
    ingest_project_file,
)


logger = logging.getLogger(__name__)


def _decode_payload(raw_payload: str) -> dict[str, Any]:
    payload = json.loads(raw_payload)
    if "project_file_id" not in payload:
        raise ValueError("Knowledge ingestion payload missing project_file_id.")
    payload["attempt_count"] = int(payload.get("attempt_count", 0))
    return payload


def _encode_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload)


def _recover_processing_jobs(redis_client: Redis) -> int:
    recovered_count = 0
    while True:
        raw_payload = redis_client.rpoplpush(
            settings.knowledge_processing_queue_name,
            settings.knowledge_queue_name,
        )
        if raw_payload is None:
            break
        recovered_count += 1
    return recovered_count


def _requeue_dead_letter_jobs(redis_client: Redis) -> int:
    requeued_count = 0
    while True:
        raw_payload = redis_client.lpop(settings.knowledge_dead_letter_queue_name)
        if raw_payload is None:
            break

        try:
            payload = _decode_payload(raw_payload)
        except Exception:
            redis_client.rpush(settings.knowledge_dead_letter_queue_name, raw_payload)
            raise

        payload["attempt_count"] = 0
        payload.pop("last_error", None)
        redis_client.rpush(settings.knowledge_queue_name, _encode_payload(payload))
        requeued_count += 1
    return requeued_count


def _reserve_next_job(redis_client: Redis) -> str | None:
    return redis_client.brpoplpush(
        settings.knowledge_queue_name,
        settings.knowledge_processing_queue_name,
        timeout=int(settings.knowledge_worker_poll_seconds),
    )


def _ack_job(redis_client: Redis, raw_payload: str) -> None:
    redis_client.lrem(settings.knowledge_processing_queue_name, 1, raw_payload)


def _retry_or_dead_letter(
    redis_client: Redis,
    *,
    raw_payload: str,
    payload: dict[str, Any],
    error: Exception,
) -> None:
    _ack_job(redis_client, raw_payload)
    payload["attempt_count"] = int(payload.get("attempt_count", 0)) + 1
    payload["last_error"] = str(error)

    is_permanent_error = (
        isinstance(error, PermanentIngestionError)
        or isinstance(
            error,
            (
                AuthenticationError,
                PermissionDeniedError,
                BadRequestError,
            ),
        )
        or (
            isinstance(error, APIStatusError)
            and error.status_code in {400, 401, 403}
        )
    )

    if (
        is_permanent_error
        or payload["attempt_count"] >= settings.knowledge_worker_max_attempts
    ):
        redis_client.rpush(
            settings.knowledge_dead_letter_queue_name,
            _encode_payload(payload),
        )
        logger.error(
            "Knowledge job moved to dead-letter queue after %s attempts: %s",
            payload["attempt_count"],
            payload.get("project_file_id"),
        )
        return

    redis_client.rpush(settings.knowledge_queue_name, _encode_payload(payload))
    logger.exception(
        "Knowledge job failed and was requeued for attempt %s: %s",
        payload["attempt_count"] + 1,
        payload.get("project_file_id"),
    )


def process_next_job(redis_client: Redis | None = None) -> bool:
    redis_client = redis_client or get_redis_client()
    raw_payload = _reserve_next_job(redis_client)
    if raw_payload is None:
        return False

    payload: dict[str, Any] = {}
    try:
        payload = _decode_payload(raw_payload)
        session_factory = get_session_factory()
        with session_factory() as db:
            ingest_project_file(
                db,
                project_file_id=str(payload["project_file_id"]),
            )
    except Exception as exc:
        _retry_or_dead_letter(
            redis_client,
            raw_payload=raw_payload,
            payload=payload,
            error=exc,
        )
        return True

    _ack_job(redis_client, raw_payload)
    logger.info("Knowledge job completed: %s", payload["project_file_id"])
    return True


def run_forever() -> None:
    logging.basicConfig(level=logging.INFO)
    redis_client = get_redis_client()
    recovered_count = _recover_processing_jobs(redis_client)
    if recovered_count:
        logger.warning("Recovered %s interrupted knowledge jobs.", recovered_count)

    if settings.knowledge_requeue_dead_letter_on_startup:
        requeued_count = _requeue_dead_letter_jobs(redis_client)
        if requeued_count:
            logger.warning(
                "Moved %s dead-letter knowledge jobs back to the main queue.",
                requeued_count,
            )

    logger.info("Knowledge worker listening on %s", settings.knowledge_queue_name)
    while True:
        processed = process_next_job(redis_client)
        if not processed:
            time.sleep(settings.knowledge_worker_poll_seconds)


def main() -> None:
    run_forever()


__all__ = ["main"]
