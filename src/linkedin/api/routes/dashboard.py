from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from linkedin.api.deps import get_current_user, get_db
from linkedin.db.models.user import User
from linkedin.schemas.dashboard import DashboardOverviewResponse, DashboardRange
from linkedin.services.dashboard import get_dashboard_overview


router = APIRouter(prefix="/dashboard")


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    summary="Get dashboard overview metrics",
)
def get_overview(
    range: DashboardRange = Query(default="month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardOverviewResponse:
    return get_dashboard_overview(db, range_name=range, user=current_user)
