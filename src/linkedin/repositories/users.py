from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from linkedin.db.models.client import Client
from linkedin.db.models.user import User


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    password_hash: str,
    role: str,
) -> User:
    user = User(
        full_name=full_name,
        email=email.strip().lower(),
        password_hash=password_hash,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(func.lower(User.email) == email.strip().lower())
    return db.scalar(statement)


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def list_users_with_client_counts(db: Session) -> list[dict[str, object]]:
    statement = (
        select(
            User.id.label("user_id"),
            User.full_name.label("name"),
            User.email.label("email"),
            func.count(Client.id).label("clients_count"),
        )
        .outerjoin(Client, Client.user_id == User.id)
        .group_by(User.id, User.full_name, User.email)
        .order_by(User.full_name.asc())
    )
    return [
        {
            "user_id": str(row.user_id),
            "name": row.name,
            "email": row.email,
            "clients_count": row.clients_count,
        }
        for row in db.execute(statement).all()
    ]


def upsert_manager_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    password_hash: str,
) -> User:
    user = get_user_by_email(db, email)
    if user is None:
        return create_user(
            db,
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            role="manager",
        )

    user.full_name = full_name
    user.password_hash = password_hash
    user.role = "manager"
    db.commit()
    db.refresh(user)
    return user
