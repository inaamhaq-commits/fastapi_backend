from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

try:
    import redis
    from redis import Redis
except ImportError:
    redis = None
    Redis = Any

from linkedin.core.config import settings


def is_redis_configured() -> bool:
    return bool(settings.redis_url)


def _default_queue_name_for_actor(actor_key: str) -> str:
    if actor_key == "wellfound_jobs":
        return settings.wellfound_queue_name
    if actor_key == "workable_jobs":
        return settings.workable_queue_name
    return settings.glassdoor_queue_name


@lru_cache
def get_redis_client() -> Redis:
    if redis is None:
        raise RuntimeError(
            "redis-py is not installed. Run `uv sync` to install Redis dependencies."
        )

    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is not configured. Add it to your .env file.")

    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        health_check_interval=30,
        socket_timeout=None,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )


def ping_redis() -> bool:
    return bool(get_redis_client().ping())


def enqueue_actor_task(
    *,
    actor_task_id: str,
    actor_key: str,
    queue_name: str | None = None,
) -> None:
    payload = {
        "actor_task_id": actor_task_id,
        "actor_key": actor_key,
    }
    get_redis_client().rpush(
        queue_name or _default_queue_name_for_actor(actor_key),
        json.dumps(payload),
    )


def enqueue_knowledge_ingestion(
    *,
    project_file_id: str,
    queue_name: str | None = None,
) -> None:
    payload = {
        "project_file_id": project_file_id,
    }
    get_redis_client().rpush(
        queue_name or settings.knowledge_queue_name,
        json.dumps(payload),
    )


def check_redis_connection() -> tuple[bool, str]:
    if redis is None:
        return False, "redis-py is not installed."

    if not settings.redis_url:
        return False, "REDIS_URL is not configured."

    try:
        connected = ping_redis()
    except Exception as exc:
        return False, f"Redis connection failed: {exc}"

    if not connected:
        return False, "Redis ping returned an unexpected response."

    return True, "Redis connection OK."
