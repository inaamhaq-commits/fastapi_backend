from __future__ import annotations

from sqlalchemy.orm import Session

from linkedin.db.models.user import User
from linkedin.db.models.user_profile import UserProfile
from linkedin.repositories.user_profiles import (
    create_user_profile,
    delete_user_profile,
    get_profile_for_user,
    list_profiles_for_user,
    list_profiles_with_client_counts,
    update_user_profile,
)
from linkedin.repositories.users import get_user_by_id
from linkedin.schemas.user_profiles import (
    ManagerUserProfileResponse,
    UserProfileCreateRequest,
    UserProfileUpdateRequest,
)


def create_profile(
    db: Session,
    payload: UserProfileCreateRequest,
    user: User,
) -> UserProfile:
    return create_user_profile(
        db,
        user_id=user.id,
        name=payload.name,
        headline=payload.headline,
        linkedin_url=str(payload.linkedin_url) if payload.linkedin_url else None,
        avatar_url=str(payload.avatar_url) if payload.avatar_url else None,
        notes=payload.notes,
    )


def list_profiles(db: Session, user: User) -> list[UserProfile]:
    return list_profiles_for_user(db, user_id=user.id)


def get_profile(db: Session, *, profile_id: str, user: User) -> UserProfile | None:
    return get_profile_for_user(db, profile_id=profile_id, user_id=user.id)


def update_profile(
    db: Session,
    *,
    profile_id: str,
    payload: UserProfileUpdateRequest,
    user: User,
) -> UserProfile | None:
    profile = get_profile_for_user(db, profile_id=profile_id, user_id=user.id)
    if profile is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if "linkedin_url" in updates:
        updates["linkedin_url"] = (
            str(payload.linkedin_url) if payload.linkedin_url else None
        )
    if "avatar_url" in updates:
        updates["avatar_url"] = str(payload.avatar_url) if payload.avatar_url else None
    return update_user_profile(profile, updates)


def delete_profile(db: Session, *, profile_id: str, user: User) -> bool:
    profile = get_profile_for_user(db, profile_id=profile_id, user_id=user.id)
    if profile is None:
        return False

    delete_user_profile(profile)
    return True


def list_manager_profiles_for_user(
    db: Session,
    *,
    target_user_id: str,
    user: User,
) -> list[ManagerUserProfileResponse] | None:
    if user.role != "manager":
        raise PermissionError("Manager access required.")
    if get_user_by_id(db, target_user_id) is None:
        return None
    return [
        ManagerUserProfileResponse.model_validate(row)
        for row in list_profiles_with_client_counts(db, user_id=target_user_id)
    ]
