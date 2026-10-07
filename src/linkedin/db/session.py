from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
import logging
from typing import Any

try:
    from sqlalchemy import Boolean, Integer, create_engine, inspect, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session, sessionmaker
except ImportError:
    Engine = Any
    Session = Any
    sessionmaker = Any
    create_engine = None
    inspect = None
    text = None
    Boolean = Any
    Integer = Any

from linkedin.core.config import settings
from linkedin.db.models import Base

logger = logging.getLogger(__name__)

CLIENT_DEFAULT_BACKFILL_COLUMNS = {
    "score",
    "calls_scheduled",
    "qualified",
    "pre_sale",
    "not_a_fit",
}
DEFAULT_BACKFILL_COLUMNS = {
    "clients": CLIENT_DEFAULT_BACKFILL_COLUMNS,
    "users": {"role"},
}


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def is_database_configured() -> bool:
    return bool(settings.database_url)


@lru_cache
def get_engine() -> Engine:
    if create_engine is None:
        raise RuntimeError(
            "SQLAlchemy is not installed. Run `uv sync` to install database dependencies."
        )

    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Add it to your environment or .env file."
        )

    return create_engine(
        normalize_database_url(settings.database_url),
        echo=settings.database_echo,
        pool_pre_ping=settings.database_pool_pre_ping,
    )


@lru_cache
def get_session_factory() -> sessionmaker:
    if sessionmaker is Any:
        raise RuntimeError(
            "SQLAlchemy is not installed. Run `uv sync` to install database dependencies."
        )

    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def ping_database() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("select 1"))


def _quote_identifier(engine: Engine, identifier: str) -> str:
    return engine.dialect.identifier_preparer.quote_identifier(identifier)


def _build_add_column_statement(engine: Engine, table_name: str, column: Any) -> str:
    return (
        f"ALTER TABLE {_quote_identifier(engine, table_name)} "
        f"ADD COLUMN IF NOT EXISTS {_quote_identifier(engine, column.name)} "
        f"{column.type.compile(dialect=engine.dialect)}"
    )


def _compile_server_default(engine: Engine, column: Any) -> str:
    server_default = column.server_default.arg
    if hasattr(server_default, "compile"):
        return str(server_default.compile(dialect=engine.dialect))
    default_text = str(server_default)
    if isinstance(column.type, (Boolean, Integer)):
        return default_text
    return "'" + default_text.replace("'", "''") + "'"


def _build_backfill_default_statement(engine: Engine, table_name: str, column: Any) -> str:
    return (
        f"UPDATE {_quote_identifier(engine, table_name)} "
        f"SET {_quote_identifier(engine, column.name)} = {_compile_server_default(engine, column)} "
        f"WHERE {_quote_identifier(engine, column.name)} IS NULL"
    )


def _build_normalize_user_roles_statement(engine: Engine) -> str:
    return (
        f"UPDATE {_quote_identifier(engine, 'users')} "
        f"SET {_quote_identifier(engine, 'role')} = 'user' "
        f"WHERE {_quote_identifier(engine, 'role')} IS NULL "
        f"OR {_quote_identifier(engine, 'role')} NOT IN ('user', 'manager')"
    )


def _build_promote_seed_manager_statement(engine: Engine) -> str:
    return (
        f"UPDATE {_quote_identifier(engine, 'users')} "
        f"SET {_quote_identifier(engine, 'role')} = 'manager' "
        f"WHERE lower({_quote_identifier(engine, 'email')}) = 'ali@invozone.com'"
    )


def _should_backfill_default(table_name: str, column: Any) -> bool:
    return (
        column.name in DEFAULT_BACKFILL_COLUMNS.get(table_name, set())
        and not column.nullable
        and column.server_default is not None
    )


def _sync_existing_table_columns(engine: Engine) -> None:
    if inspect is None or text is None:
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if not existing_tables:
        return

    with engine.begin() as connection:
        for metadata_table in Base.metadata.sorted_tables:
            if metadata_table.name not in existing_tables:
                continue

            existing_columns = {
                column_info["name"]
                for column_info in inspector.get_columns(metadata_table.name)
            }
            for column in metadata_table.columns:
                if column.name in existing_columns:
                    continue

                connection.execute(
                    text(
                        _build_add_column_statement(
                            engine,
                            metadata_table.name,
                            column,
                        )
                    )
                )
                logger.info(
                    "Added missing database column %s.%s",
                    metadata_table.name,
                    column.name,
                )
            for column in metadata_table.columns:
                if not _should_backfill_default(metadata_table.name, column):
                    continue

                connection.execute(
                    text(
                        _build_backfill_default_statement(
                            engine,
                            metadata_table.name,
                            column,
                        )
                    )
                )
            if metadata_table.name == "users" and "role" in existing_columns:
                connection.execute(text(_build_normalize_user_roles_statement(engine)))
                connection.execute(text(_build_promote_seed_manager_statement(engine)))


def create_database_tables() -> None:
    if create_engine is None or not settings.database_url:
        return
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _sync_existing_table_columns(engine)


def check_database_connection() -> tuple[bool, str]:
    if create_engine is None:
        return False, "SQLAlchemy is not installed."

    if not settings.database_url:
        return False, "DATABASE_URL is not configured."

    try:
        ping_database()
    except Exception as exc:
        return False, f"Database connection failed: {exc}"

    return True, "Database connection OK."
