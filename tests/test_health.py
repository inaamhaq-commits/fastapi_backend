import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from linkedin.app import create_app
from linkedin.main import app
from linkedin.schemas.health import DependencyHealth, HealthResponse
from linkedin.services.health import get_health_status


class HealthRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_root_route(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["docs"], "/docs")

    @patch("linkedin.api.routes.health.get_health_status")
    def test_health_route_when_dependencies_are_connected(
        self,
        mock_get_health_status,
    ) -> None:
        mock_get_health_status.return_value = HealthResponse(
            status="ok",
            app_name="LinkedIn API",
            version="0.1.0",
            database=DependencyHealth(
                configured=True,
                connected=True,
                message="Database connection OK.",
            ),
            redis=DependencyHealth(
                configured=True,
                connected=True,
                message="Redis connection OK.",
            ),
        )

        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(response.json()["database"]["connected"])
        self.assertTrue(response.json()["redis"]["connected"])

    @patch("linkedin.api.routes.health.get_health_status")
    def test_health_route_when_any_dependency_is_disconnected(
        self,
        mock_get_health_status,
    ) -> None:
        mock_get_health_status.return_value = HealthResponse(
            status="degraded",
            app_name="LinkedIn API",
            version="0.1.0",
            database=DependencyHealth(
                configured=True,
                connected=False,
                message="Database connection failed.",
            ),
            redis=DependencyHealth(
                configured=True,
                connected=True,
                message="Redis connection OK.",
            ),
        )

        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "degraded")
        self.assertFalse(response.json()["database"]["connected"])
        self.assertTrue(response.json()["redis"]["connected"])

    @patch("linkedin.app.settings")
    @patch("linkedin.app.create_database_tables")
    def test_app_starts_when_database_startup_fails_without_fail_fast(
        self,
        mock_create_database_tables,
        mock_settings,
    ) -> None:
        mock_settings.app_name = "LinkedIn API"
        mock_settings.app_version = "0.1.0"
        mock_settings.debug = False
        mock_settings.cors_allow_origins = []
        mock_settings.api_v1_prefix = "/api/v1"
        mock_settings.database_url = "postgresql://example"
        mock_settings.database_check_on_startup = True
        mock_settings.database_fail_fast = False
        mock_create_database_tables.side_effect = RuntimeError("database unavailable")

        with TestClient(create_app()) as client:
            response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)


class HealthServiceTests(unittest.TestCase):
    @patch("linkedin.services.health.check_database_connection")
    @patch("linkedin.services.health.is_database_configured")
    @patch("linkedin.services.health.check_redis_connection")
    @patch("linkedin.services.health.is_redis_configured")
    def test_get_health_status_when_dependencies_are_connected(
        self,
        mock_is_redis_configured,
        mock_check_redis_connection,
        mock_is_database_configured,
        mock_check_database_connection,
    ) -> None:
        mock_is_database_configured.return_value = True
        mock_is_redis_configured.return_value = True
        mock_check_database_connection.return_value = (True, "Database connection OK.")
        mock_check_redis_connection.return_value = (True, "Redis connection OK.")

        health = get_health_status()

        self.assertEqual(health.status, "ok")
        self.assertTrue(health.database.connected)
        self.assertTrue(health.database.configured)
        self.assertTrue(health.redis.connected)
        self.assertTrue(health.redis.configured)

    @patch("linkedin.services.health.check_database_connection")
    @patch("linkedin.services.health.is_database_configured")
    @patch("linkedin.services.health.check_redis_connection")
    @patch("linkedin.services.health.is_redis_configured")
    def test_get_health_status_when_database_is_disconnected(
        self,
        mock_is_redis_configured,
        mock_check_redis_connection,
        mock_is_database_configured,
        mock_check_database_connection,
    ) -> None:
        mock_is_database_configured.return_value = True
        mock_is_redis_configured.return_value = True
        mock_check_database_connection.return_value = (
            False,
            "Database connection failed.",
        )
        mock_check_redis_connection.return_value = (True, "Redis connection OK.")

        health = get_health_status()

        self.assertEqual(health.status, "degraded")
        self.assertFalse(health.database.connected)
        self.assertTrue(health.database.configured)
        self.assertTrue(health.redis.connected)

    @patch("linkedin.services.health.check_database_connection")
    @patch("linkedin.services.health.is_database_configured")
    @patch("linkedin.services.health.check_redis_connection")
    @patch("linkedin.services.health.is_redis_configured")
    def test_get_health_status_when_redis_is_disconnected(
        self,
        mock_is_redis_configured,
        mock_check_redis_connection,
        mock_is_database_configured,
        mock_check_database_connection,
    ) -> None:
        mock_is_database_configured.return_value = True
        mock_is_redis_configured.return_value = True
        mock_check_database_connection.return_value = (True, "Database connection OK.")
        mock_check_redis_connection.return_value = (
            False,
            "Redis connection failed.",
        )

        health = get_health_status()

        self.assertEqual(health.status, "degraded")
        self.assertTrue(health.database.connected)
        self.assertFalse(health.redis.connected)
        self.assertTrue(health.redis.configured)
