from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from linkedin.api.router import api_router
from linkedin.api.routes.root import router as root_router
from linkedin.core.config import settings
from linkedin.db.session import create_database_tables, ping_database
from linkedin.integrations.minio import ensure_minio_bucket, is_minio_configured


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.database_url:
        try:
            create_database_tables()
            if settings.database_check_on_startup:
                ping_database()
        except Exception:
            if settings.database_fail_fast:
                raise
            logger.warning("Database startup failed; continuing without DB connection.")
    if is_minio_configured():
        try:
            ensure_minio_bucket()
        except Exception:
            if settings.database_fail_fast:
                raise
            logger.warning("MinIO startup failed; continuing without bucket check.")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(root_router, tags=["meta"])
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app
