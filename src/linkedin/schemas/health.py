from typing import Literal

from pydantic import BaseModel


class DependencyHealth(BaseModel):
    configured: bool
    connected: bool
    message: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app_name: str
    version: str
    database: DependencyHealth
    redis: DependencyHealth
