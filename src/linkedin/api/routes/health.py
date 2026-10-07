from fastapi import APIRouter, Response, status

from linkedin.schemas.health import HealthResponse
from linkedin.services.health import get_health_status


router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health check")
def read_health(response: Response) -> HealthResponse:
    health = get_health_status()
    if health.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health
