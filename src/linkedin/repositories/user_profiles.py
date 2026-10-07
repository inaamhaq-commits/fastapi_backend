from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, object_session

from linkedin.db.models.client import Client
from linkedin.db.models.user_profile import UserProfile


def create_user_profile(
    db: Session,
    *,
    user_id: str,
    name: str,
    headline: str | None,
    linkedin_url: str | None,
    avatar_url: str | None,
    notes: str | None,
) -> UserProfile:
    profile = UserProfile(
        user_id=user_id,
        name=name,
        headline=headline,
        linkedin_url=linkedin_url,
        avatar_url=avatar_url,
        notes=notes,
        is_active=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def list_profiles_for_user(db: Session, *, user_id: str) -> list[UserProfile]:
    statement = (
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .order_by(UserProfile.created_at.desc())
    )
    return list(db.scalars(statement).all())


def get_profile_for_user(
    db: Session,
    *,
    profile_id: str,
    user_id: str,
) -> UserProfile | None:
    statement = select(UserProfile).where(
        UserProfile.id == profile_id,
        UserProfile.user_id == user_id,
    )
    return db.scalars(statement).first()


def get_profile_by_id(db: Session, profile_id: str) -> UserProfile | None:
    return db.get(UserProfile, profile_id)


def update_user_profile(
    profile: UserProfile,
    updates: dict[str, object],
) -> UserProfile:
    for field_name, value in updates.items():
        setattr(profile, field_name, value)
    db = object_session(profile)
    if db is None:
        raise RuntimeError("Profile is not attached to a database session.")
    db.commit()
    db.refresh(profile)
    return profile


def delete_user_profile(profile: UserProfile) -> None:
    db = object_session(profile)
    if db is None:
        raise RuntimeError("Profile is not attached to a database session.")
    db.delete(profile)
    db.commit()


def list_profiles_with_client_counts(
    db: Session,
    *,
    user_id: str,
) -> list[dict[str, object]]:
    statement = (
        select(
            UserProfile,
            func.count(Client.id).label("clients_count"),
        )
        .outerjoin(Client, Client.profile_id == UserProfile.id)
        .where(UserProfile.user_id == user_id)
        .group_by(UserProfile.id)
        .order_by(UserProfile.created_at.desc())
    )
    return [
        {
            **profile.__dict__,
            "clients_count": clients_count,
        }
        for profile, clients_count in db.execute(statement).all()
    ]
