from fastapi import APIRouter

from linkedin.core.config import settings


router = APIRouter()


@router.get("/", summary="Service status")
def read_root() -> dict[str, str]:
    return {
        "message": f"{settings.app_name} is running",
        "docs": "/docs",
    }
