from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="LinkedIn API", validation_alias="APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        validation_alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_origin_regex: str | None = Field(
        default=".*",
        validation_alias="CORS_ALLOW_ORIGIN_REGEX",
    )
    auth_jwt_secret_key: str = Field(
        default="change-me-in-production",
        validation_alias="AUTH_JWT_SECRET_KEY",
    )
    auth_access_token_minutes: int = Field(
        default=15,
        validation_alias="AUTH_ACCESS_TOKEN_MINUTES",
    )
    auth_refresh_token_days: int = Field(
        default=30,
        validation_alias="AUTH_REFRESH_TOKEN_DAYS",
    )
    auth_access_cookie_name: str = Field(
        default="access_token",
        validation_alias="AUTH_ACCESS_COOKIE_NAME",
    )
    auth_refresh_cookie_name: str = Field(
        default="refresh_token",
        validation_alias="AUTH_REFRESH_COOKIE_NAME",
    )
    auth_cookie_secure: bool = Field(
        default=False,
        validation_alias="AUTH_COOKIE_SECURE",
    )
    auth_cookie_samesite: Literal["lax", "strict", "none"] = Field(
        default="lax",
        validation_alias="AUTH_COOKIE_SAMESITE",
    )
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")
    database_pool_pre_ping: bool = Field(
        default=True,
        validation_alias="DATABASE_POOL_PRE_PING",
    )
    database_check_on_startup: bool = Field(
        default=True,
        validation_alias="DATABASE_CHECK_ON_STARTUP",
    )
    database_fail_fast: bool = Field(
        default=False,
        validation_alias="DATABASE_FAIL_FAST",
    )
    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")
    knowledge_queue_name: str = Field(
        default="queue:knowledge-ingestion",
        validation_alias="KNOWLEDGE_QUEUE_NAME",
    )
    knowledge_processing_queue_name: str = Field(
        default="queue:knowledge-ingestion:processing",
        validation_alias="KNOWLEDGE_PROCESSING_QUEUE_NAME",
    )
    knowledge_dead_letter_queue_name: str = Field(
        default="queue:knowledge-ingestion:dead-letter",
        validation_alias="KNOWLEDGE_DEAD_LETTER_QUEUE_NAME",
    )
    knowledge_worker_poll_seconds: float = Field(
        default=2.0,
        validation_alias="KNOWLEDGE_WORKER_POLL_SECONDS",
    )
    knowledge_worker_max_attempts: int = Field(
        default=3,
        validation_alias="KNOWLEDGE_WORKER_MAX_ATTEMPTS",
    )
    knowledge_requeue_dead_letter_on_startup: bool = Field(
        default=True,
        validation_alias="KNOWLEDGE_REQUEUE_DEAD_LETTER_ON_STARTUP",
    )
    minio_endpoint_url: str | None = Field(
        default=None,
        validation_alias="MINIO_ENDPOINT_URL",
    )
    minio_public_url: str | None = Field(
        default=None,
        validation_alias="MINIO_PUBLIC_URL",
    )
    minio_access_key: str | None = Field(
        default=None,
        validation_alias="MINIO_ACCESS_KEY",
    )
    minio_secret_key: str | None = Field(
        default=None,
        validation_alias="MINIO_SECRET_KEY",
    )
    minio_bucket_name: str = Field(
        default="knowledge-base",
        validation_alias="MINIO_BUCKET_NAME",
    )
    minio_presigned_url_seconds: int = Field(
        default=900,
        validation_alias="MINIO_PRESIGNED_URL_SECONDS",
    )
    qdrant_url: str = Field(default="http://localhost:6333", validation_alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, validation_alias="QDRANT_API_KEY")
    qdrant_collection_name: str = Field(
        default="knowledge_chunks",
        validation_alias="QDRANT_COLLECTION_NAME",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(
        default=1536,
        validation_alias="EMBEDDING_DIMENSIONS",
    )
    knowledge_chunk_size_tokens: int = Field(
        default=800,
        validation_alias="KNOWLEDGE_CHUNK_SIZE_TOKENS",
    )
    knowledge_chunk_overlap_tokens: int = Field(
        default=160,
        validation_alias="KNOWLEDGE_CHUNK_OVERLAP_TOKENS",
    )
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(
        default="gpt-5.6-terra",
        validation_alias="OPENAI_MODEL",
    )
    apify_api_token: str | None = Field(default=None, validation_alias="APIFY_API_TOKEN")
    glassdoor_actor_id: str = Field(
        default="5OaooRg0FxlRF0L1B",
        validation_alias="GLASSDOOR_ACTOR_ID",
    )
    glassdoor_queue_name: str = Field(
        default="queue:actors",
        validation_alias="GLASSDOOR_QUEUE_NAME",
    )
    glassdoor_source_site: str = Field(
        default="glassdoor",
        validation_alias="GLASSDOOR_SOURCE_SITE",
    )
    wellfound_actor_id: str = Field(
        default="jV4Y8h6j3AqVj5Qur",
        validation_alias="WELLFOUND_ACTOR_ID",
    )
    wellfound_queue_name: str = Field(
        default="queue:wellfound-actors",
        validation_alias="WELLFOUND_QUEUE_NAME",
    )
    wellfound_source_site: str = Field(
        default="wellfound",
        validation_alias="WELLFOUND_SOURCE_SITE",
    )
    workable_actor_id: str = Field(
        default="hXENKfdQC3e6E9ecv",
        validation_alias="WORKABLE_ACTOR_ID",
    )
    workable_queue_name: str = Field(
        default="queue:workable-actors",
        validation_alias="WORKABLE_QUEUE_NAME",
    )
    workable_source_site: str = Field(
        default="workable",
        validation_alias="WORKABLE_SOURCE_SITE",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
