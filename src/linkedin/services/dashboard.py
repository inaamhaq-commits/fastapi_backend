from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from linkedin.db.models.user import User
from linkedin.repositories.dashboard import get_client_overview_counts, list_user_lead_counts
from linkedin.schemas.dashboard import (
    DashboardOverviewResponse,
    DashboardRange,
    ManagerDashboardResponse,
    ManagerLeadTotalsResponse,
    ManagerUserDashboardResponse,
)


class ManagerPermissionError(Exception):
    pass


RANGE_LABELS: dict[DashboardRange, str] = {
    "week": "This Week",
    "month": "This Month",
    "3month": "Last 3 Months",
}

RANGE_DURATIONS: dict[DashboardRange, timedelta] = {
    "week": timedelta(days=7),
    "month": timedelta(days=30),
    "3month": timedelta(days=90),
}


def get_dashboard_overview(
    db: Session,
    *,
    range_name: DashboardRange,
    user: User,
) -> DashboardOverviewResponse:
    since = datetime.now(UTC) - RANGE_DURATIONS[range_name]
    counts = get_client_overview_counts(db, user_id=user.id, since=since)
    return DashboardOverviewResponse(
        label=RANGE_LABELS[range_name],
        **counts,
    )


def get_manager_dashboard(db: Session, *, user: User) -> ManagerDashboardResponse:
    if user.role != "manager":
        raise ManagerPermissionError("Manager access required.")

    users = []
    totals = {
        "total_leads": 0,
        "calls_scheduled": 0,
        "qualified": 0,
        "pre_sale": 0,
        "not_a_fit": 0,
    }
    for row in list_user_lead_counts(db):
        leads = {
            "total_leads": row["total_leads"],
            "calls_scheduled": row["calls_scheduled"],
            "qualified": row["qualified"],
            "pre_sale": row["pre_sale"],
            "not_a_fit": row["not_a_fit"],
        }
        for key, value in leads.items():
            totals[key] += value
        users.append(
            ManagerUserDashboardResponse(
                user_id=row["user_id"],
                name=row["name"],
                email=row["email"],
                leads=ManagerLeadTotalsResponse(**leads),
            )
        )

    return ManagerDashboardResponse(
        totals=ManagerLeadTotalsResponse(**totals),
        users=users,
    )
