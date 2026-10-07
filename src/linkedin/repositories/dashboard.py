from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from linkedin.db.models.client import Client
from linkedin.db.models.user import User


def get_client_overview_counts(
    db: Session,
    *,
    user_id: str,
    since: datetime,
) -> dict[str, int]:
    statement = select(
        func.count(Client.id).label("leads_generated"),
        func.count(Client.id).filter(Client.calls_scheduled.is_(True)).label(
            "calls_scheduled"
        ),
        func.count(Client.id).filter(Client.qualified.is_(True)).label("qualified"),
        func.count(Client.id).filter(Client.pre_sale.is_(True)).label("pre_sale"),
        func.count(Client.id).filter(Client.not_a_fit.is_(True)).label("not_a_fit"),
    ).where(
        Client.user_id == user_id,
        Client.created_at >= since,
    )
    row = db.execute(statement).one()
    return {
        "leads_generated": row.leads_generated,
        "calls_scheduled": row.calls_scheduled,
        "qualified": row.qualified,
        "pre_sale": row.pre_sale,
        "not_a_fit": row.not_a_fit,
    }


def list_user_lead_counts(db: Session) -> list[dict[str, object]]:
    statement = (
        select(
            User.id.label("user_id"),
            User.full_name.label("name"),
            User.email.label("email"),
            func.count(Client.id).label("total_leads"),
            func.count(Client.id).filter(Client.calls_scheduled.is_(True)).label(
                "calls_scheduled"
            ),
            func.count(Client.id).filter(Client.qualified.is_(True)).label("qualified"),
            func.count(Client.id).filter(Client.pre_sale.is_(True)).label("pre_sale"),
            func.count(Client.id).filter(Client.not_a_fit.is_(True)).label("not_a_fit"),
        )
        .outerjoin(Client, Client.user_id == User.id)
        .group_by(User.id, User.full_name, User.email)
        .order_by(User.full_name.asc())
    )
    rows = db.execute(statement).all()
    return [
        {
            "user_id": str(row.user_id),
            "name": row.name,
            "email": row.email,
            "total_leads": row.total_leads,
            "calls_scheduled": row.calls_scheduled,
            "qualified": row.qualified,
            "pre_sale": row.pre_sale,
            "not_a_fit": row.not_a_fit,
        }
        for row in rows
    ]
