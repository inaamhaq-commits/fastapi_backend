from __future__ import annotations

from sqlalchemy.orm import Session

from linkedin.db.models.client import Client
from linkedin.db.models.user import User
from linkedin.repositories.clients import (
    create_client,
    get_client_for_user,
    list_all_clients,
    list_clients_by_profile_id,
    list_clients_by_user_id_and_profile_id,
    list_clients_by_user_id,
    list_clients_for_user,
    update_client,
)
from linkedin.repositories.user_profiles import get_profile_by_id, get_profile_for_user
from linkedin.repositories.users import get_user_by_id, list_users_with_client_counts
from linkedin.schemas.clients import (
    CLIENT_STAGE_FIELDS,
    ClientCreateRequest,
    ManagerUserClientCountResponse,
    ClientUpdateRequest,
)


def create_client_profile(db: Session, payload: ClientCreateRequest, user: User) -> Client:
    profile_id = str(payload.profile_id) if payload.profile_id else None
    if profile_id is not None and get_profile_for_user(
        db,
        profile_id=profile_id,
        user_id=user.id,
    ) is None:
        raise PermissionError("Profile does not belong to this user.")

    return create_client(
        db,
        user_id=user.id,
        profile_id=profile_id,
        name=payload.name,
        company=payload.company,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        linkedin_url=str(payload.linkedin_url) if payload.linkedin_url else None,
        notes=payload.notes,
        score=payload.score,
        calls_scheduled=payload.calls_scheduled,
        qualified=payload.qualified,
        pre_sale=payload.pre_sale,
        not_a_fit=payload.not_a_fit,
    )


def list_client_profiles(db: Session, user: User) -> list[Client]:
    return list_clients_for_user(db, user_id=user.id)


def list_client_profiles_for_profile(
    db: Session,
    *,
    profile_id: str,
    user: User,
) -> list[Client] | None:
    profile = get_profile_by_id(db, profile_id)
    if profile is None:
        return None
    if user.role != "manager" and profile.user_id != user.id:
        raise PermissionError("Profile does not belong to this user.")
    return list_clients_by_profile_id(db, profile_id=profile_id)


def list_manager_client_profiles(db: Session, user: User) -> list[Client]:
    if user.role != "manager":
        raise PermissionError("Manager access required.")
    return list_all_clients(db)


def list_manager_users_with_client_counts(
    db: Session,
    user: User,
) -> list[ManagerUserClientCountResponse]:
    if user.role != "manager":
        raise PermissionError("Manager access required.")
    return [
        ManagerUserClientCountResponse.model_validate(row)
        for row in list_users_with_client_counts(db)
    ]


def list_manager_client_profiles_for_user(
    db: Session,
    *,
    target_user_id: str,
    user: User,
) -> list[Client] | None:
    if user.role != "manager":
        raise PermissionError("Manager access required.")
    if get_user_by_id(db, target_user_id) is None:
        return None
    return list_clients_by_user_id(db, user_id=target_user_id)


def list_manager_client_profiles_for_user_profile(
    db: Session,
    *,
    target_user_id: str,
    profile_id: str,
    user: User,
) -> list[Client] | None:
    if user.role != "manager":
        raise PermissionError("Manager access required.")
    if get_user_by_id(db, target_user_id) is None:
        return None
    if get_profile_for_user(
        db,
        profile_id=profile_id,
        user_id=target_user_id,
    ) is None:
        return None
    return list_clients_by_user_id_and_profile_id(
        db,
        user_id=target_user_id,
        profile_id=profile_id,
    )


def get_client_profile(db: Session, *, client_id: str, user: User) -> Client | None:
    return get_client_for_user(db, client_id=client_id, user_id=user.id)


def update_client_profile(
    db: Session,
    *,
    client_id: str,
    payload: ClientUpdateRequest,
    user: User,
) -> Client | None:
    client = get_client_for_user(db, client_id=client_id, user_id=user.id)
    if client is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if "profile_id" in updates and updates["profile_id"] is not None:
        profile_id = str(updates["profile_id"])
        if get_profile_for_user(
            db,
            profile_id=profile_id,
            user_id=user.id,
        ) is None:
            raise PermissionError("Profile does not belong to this user.")
        updates["profile_id"] = profile_id
    if "email" in updates:
        updates["email"] = str(payload.email) if payload.email else None
    if "linkedin_url" in updates:
        updates["linkedin_url"] = (
            str(payload.linkedin_url) if payload.linkedin_url else None
        )
    selected_stage = next(
        (
            field_name
            for field_name in CLIENT_STAGE_FIELDS
            if updates.get(field_name) is True
        ),
        None,
    )
    if selected_stage is not None:
        for field_name in CLIENT_STAGE_FIELDS:
            updates[field_name] = field_name == selected_stage

    return update_client(client, updates)
