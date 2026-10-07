# LinkedIn API

A clean FastAPI backend scaffold with a Supabase-ready Postgres connection layer.

## Folder Structure

```text
.
|-- .env.example
|-- pyproject.toml
|-- README.md
|-- src
|   `-- linkedin
|       |-- __init__.py
|       |-- __main__.py
|       |-- app.py
|       |-- main.py
|       |-- api
|       |   |-- __init__.py
|       |   |-- deps.py
|       |   |-- router.py
|       |   `-- routes
|       |       |-- __init__.py
|       |       |-- health.py
|       |       `-- root.py
|       |-- core
|       |   |-- __init__.py
|       |   `-- config.py
|       |-- db
|       |   |-- __init__.py
|       |   `-- session.py
|       |-- repositories
|       |   `-- __init__.py
|       |-- schemas
|       |   |-- __init__.py
|       |   `-- health.py
|       `-- services
|           |-- __init__.py
|           `-- health.py
`-- tests
    |-- __init__.py
    |-- test_db_session.py
    `-- test_health.py
```

## Why This Structure

- `main.py` is the FastAPI app entrypoint.
- `app.py` creates the app and handles startup behavior.
- `api/routes` contains HTTP endpoints only.
- `api/deps.py` contains reusable dependencies like the database session.
- `db/session.py` contains the SQLAlchemy engine and session factory.
- `repositories` is where database query logic should live once we build the chat feature.
- `core/config.py` centralizes environment-driven settings.

## Supabase Setup

1. Copy `.env.example` to `.env`.
2. Put your Supabase Postgres connection string in `DATABASE_URL`.
3. Run `uv sync`.
4. Start the server with `uv run fastapi dev`.

For this long-running FastAPI backend, prefer:

- Direct connection on port `5432` if your environment can reach Supabase over IPv6.
- Supavisor session mode on port `5432` if your environment is IPv4-only.

Avoid Supavisor transaction mode for this app runtime because it is meant for short-lived or serverless connections.

If local DNS or network access to Supabase is flaky during development, keep `DATABASE_FAIL_FAST=false` so the app can still boot while logging the database startup failure.

## Commands

```bash
uv sync
uv run fastapi dev
uv run linkedin
uv run python -m unittest
```
