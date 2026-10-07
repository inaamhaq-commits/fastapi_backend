from linkedin.core.config import settings
from linkedin.db.session import check_database_connection, is_database_configured
from linkedin.schemas.health import DependencyHealth, HealthResponse


def get_health_status() -> HealthResponse:
    database_connected, database_message = check_database_connection()

    return HealthResponse(
        status="ok" if database_connected else "degraded",
        app_name=settings.app_name,
        version=settings.app_version,
        database=DependencyHealth(
            configured=is_database_configured(),
            connected=database_connected,
            message=database_message,
        ),
    )
