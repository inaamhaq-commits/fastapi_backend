import unittest
from unittest.mock import Mock, patch

from sqlalchemy import create_engine

from linkedin.db.models.client import Client
from linkedin.db.models.job_posting import JobPosting
from linkedin.db.session import normalize_database_url, _sync_existing_table_columns


class DatabaseSessionTests(unittest.TestCase):
    def test_normalize_postgres_url(self) -> None:
        url = "postgres://user:pass@localhost:5432/postgres"

        self.assertEqual(
            normalize_database_url(url),
            "postgresql+psycopg://user:pass@localhost:5432/postgres",
        )

    def test_keep_psycopg_url(self) -> None:
        url = "postgresql+psycopg://user:pass@localhost:5432/postgres"

        self.assertEqual(normalize_database_url(url), url)

    @patch("linkedin.db.session.inspect")
    def test_sync_existing_table_columns_adds_missing_columns(self, mock_inspect) -> None:
        sqlite_engine = create_engine("sqlite://")
        engine = Mock()
        engine.dialect = sqlite_engine.dialect

        connection = Mock()
        transaction = Mock()
        transaction.__enter__ = Mock(return_value=connection)
        transaction.__exit__ = Mock(return_value=False)
        engine.begin.return_value = transaction

        inspector = mock_inspect.return_value
        inspector.get_table_names.return_value = ["job_postings"]
        inspector.get_columns.return_value = [
            {"name": column.name}
            for column in JobPosting.__table__.columns
            if column.name != "company_website_url"
        ]

        _sync_existing_table_columns(engine)

        executed = [str(call.args[0]) for call in connection.execute.call_args_list]
        alter_statements = [
            statement for statement in executed if "ALTER TABLE" in statement
        ]
        self.assertEqual(len(alter_statements), 1)
        self.assertIn("company_website_url", alter_statements[0])

    @patch("linkedin.db.session.inspect")
    def test_sync_existing_table_columns_backfills_server_defaults(self, mock_inspect) -> None:
        sqlite_engine = create_engine("sqlite://")
        engine = Mock()
        engine.dialect = sqlite_engine.dialect

        connection = Mock()
        transaction = Mock()
        transaction.__enter__ = Mock(return_value=connection)
        transaction.__exit__ = Mock(return_value=False)
        engine.begin.return_value = transaction

        inspector = mock_inspect.return_value
        inspector.get_table_names.return_value = ["clients"]
        inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "user_id"},
            {"name": "name"},
            {"name": "company"},
            {"name": "email"},
            {"name": "phone"},
            {"name": "linkedin_url"},
            {"name": "notes"},
            {"name": "score"},
            {"name": "calls_scheduled"},
            {"name": "qualified"},
            {"name": "pre_sale"},
            {"name": "not_a_fit"},
            {"name": "needs_follow_up"},
            {"name": "is_active"},
            {"name": "status"},
            {"name": "created_at"},
            {"name": "updated_at"},
        ]

        _sync_existing_table_columns(engine)

        executed = [str(call.args[0]) for call in connection.execute.call_args_list]
        self.assertTrue(
            any(
                'UPDATE "clients" SET "calls_scheduled" = false '
                'WHERE "calls_scheduled" IS NULL' in statement
                for statement in executed
            )
        )

    @patch("linkedin.db.session.inspect")
    def test_sync_existing_table_columns_does_not_backfill_status(self, mock_inspect) -> None:
        sqlite_engine = create_engine("sqlite://")
        engine = Mock()
        engine.dialect = sqlite_engine.dialect

        connection = Mock()
        transaction = Mock()
        transaction.__enter__ = Mock(return_value=connection)
        transaction.__exit__ = Mock(return_value=False)
        engine.begin.return_value = transaction

        inspector = mock_inspect.return_value
        inspector.get_table_names.return_value = ["clients"]
        inspector.get_columns.return_value = [
            {"name": column.name} for column in Client.__table__.columns
        ]

        _sync_existing_table_columns(engine)

        executed = [str(call.args[0]) for call in connection.execute.call_args_list]
        self.assertFalse(
            any('SET "status" = new' in statement for statement in executed)
        )

    @patch("linkedin.db.session.inspect")
    def test_sync_existing_table_columns_normalizes_user_roles(self, mock_inspect) -> None:
        sqlite_engine = create_engine("sqlite://")
        engine = Mock()
        engine.dialect = sqlite_engine.dialect

        connection = Mock()
        transaction = Mock()
        transaction.__enter__ = Mock(return_value=connection)
        transaction.__exit__ = Mock(return_value=False)
        engine.begin.return_value = transaction

        inspector = mock_inspect.return_value
        inspector.get_table_names.return_value = ["users"]
        inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "full_name"},
            {"name": "email"},
            {"name": "password_hash"},
            {"name": "role"},
            {"name": "created_at"},
            {"name": "updated_at"},
        ]

        _sync_existing_table_columns(engine)

        executed = [str(call.args[0]) for call in connection.execute.call_args_list]
        self.assertTrue(
            any(
                "\"role\" NOT IN ('user', 'manager')" in statement
                for statement in executed
            )
        )
        self.assertTrue(
            any("ali@invozone.com" in statement and "manager" in statement for statement in executed)
        )
