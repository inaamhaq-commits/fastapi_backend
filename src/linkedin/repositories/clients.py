from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from linkedin.core.enums import ClientStatus
from linkedin.db.models.client import Client


def create_client(
    db: Session,
    *,
    user_id: str,
    profile_id: str | None,
    name: str,
    company: str,
    email: str | None,
    phone: str | None,
    linkedin_url: str | None,
    notes: str | None,
    score: int,
    calls_scheduled: bool,
    qualified: bool,
    pre_sale: bool,
    not_a_fit: bool,
) -> Client:
    client = Client(
        user_id=user_id,
        profile_id=profile_id,
        name=name,
        company=company,
        email=email.lower() if email else None,
        phone=phone,
        linkedin_url=linkedin_url,
        notes=notes,
        score=score,
        calls_scheduled=calls_scheduled,
        qualified=qualified,
        pre_sale=pre_sale,
        not_a_fit=not_a_fit,
        needs_follow_up=False,
        is_active=True,
        status=ClientStatus.NEW.value,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def list_clients_for_user(db: Session, *, user_id: str) -> list[Client]:
    statement = (
        select(Client)
        .where(Client.user_id == user_id)
        .order_by(Client.created_at.desc())
    )
    return list(db.scalars(statement).all())


def list_all_clients(db: Session) -> list[Client]:
    statement = select(Client).order_by(Client.created_at.desc())
    return list(db.scalars(statement).all())


def list_clients_by_user_id(db: Session, *, user_id: str) -> list[Client]:
    statement = (
        select(Client)
        .where(Client.user_id == user_id)
        .order_by(Client.created_at.desc())
    )
    return list(db.scalars(statement).all())


def list_clients_by_user_id_and_profile_id(
    db: Session,
    *,
    user_id: str,
    profile_id: str,
) -> list[Client]:
    statement = (
        select(Client)
        .where(
            Client.user_id == user_id,
            Client.profile_id == profile_id,
        )
        .order_by(Client.created_at.desc())
    )
    return list(db.scalars(statement).all())


def list_clients_by_profile_id(db: Session, *, profile_id: str) -> list[Client]:
    statement = (
        select(Client)
        .where(Client.profile_id == profile_id)
        .order_by(Client.created_at.desc())
    )
    return list(db.scalars(statement).all())


def get_client_for_user(
    db: Session,
    *,
    client_id: str,
    user_id: str,
) -> Client | None:
    statement = select(Client).where(
        Client.id == client_id,
        Client.user_id == user_id,
    )
    return db.scalars(statement).first()


def update_client(client: Client, updates: dict[str, object]) -> Client:
    for field_name, value in updates.items():
        setattr(client, field_name, value)
    db = object_session(client)
    if db is None:
        raise RuntimeError("Client is not attached to a database session.")
    db.commit()
    db.refresh(client)
    return client
