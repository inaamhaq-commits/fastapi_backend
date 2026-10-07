from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from linkedin.api.deps import get_current_user, get_db
from linkedin.db.models.user import User
from linkedin.schemas.clients import ClientResponse, ManagerUserClientCountResponse
from linkedin.schemas.dashboard import ManagerDashboardResponse
from linkedin.services.clients import (
    list_manager_client_profiles,
    list_manager_client_profiles_for_user_profile,
    list_manager_client_profiles_for_user,
    list_manager_users_with_client_counts,
)
from linkedin.services.dashboard import ManagerPermissionError, get_manager_dashboard
from linkedin.schemas.user_profiles import ManagerUserProfileResponse
from linkedin.services.user_profiles import list_manager_profiles_for_user


router = APIRouter(prefix="/manager")


@router.get(
    "/dashboard",
    response_model=ManagerDashboardResponse,
    summary="Get manager dashboard metrics across users",
)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManagerDashboardResponse:
    try:
        return get_manager_dashboard(db, user=current_user)
    except ManagerPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get(
    "/clients",
    response_model=list[ClientResponse],
    summary="List all client profiles for managers",
)
def list_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClientResponse]:
    try:
        return [
            ClientResponse.model_validate(client)
            for client in list_manager_client_profiles(db, current_user)
        ]
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get(
    "/users",
    response_model=list[ManagerUserClientCountResponse],
    summary="List users with client counts for managers",
)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ManagerUserClientCountResponse]:
    try:
        return list_manager_users_with_client_counts(db, current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get(
    "/users/{user_id}/clients",
    response_model=list[ClientResponse],
    summary="List a user's client profiles for managers",
)
def list_user_clients(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClientResponse]:
    try:
        clients = list_manager_client_profiles_for_user(
            db,
            target_user_id=user_id,
            user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if clients is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return [ClientResponse.model_validate(client) for client in clients]


@router.get(
    "/users/{user_id}/profiles",
    response_model=list[ManagerUserProfileResponse],
    summary="List a user's source profiles for managers",
)
def list_user_profiles(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ManagerUserProfileResponse]:
    try:
        profiles = list_manager_profiles_for_user(
            db,
            target_user_id=user_id,
            user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if profiles is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return profiles


@router.get(
    "/users/{user_id}/profiles/{profile_id}/clients",
    response_model=list[ClientResponse],
    summary="List a user's client profiles for one source profile",
)
def list_user_profile_clients(
    user_id: str,
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClientResponse]:
    try:
        clients = list_manager_client_profiles_for_user_profile(
            db,
            target_user_id=user_id,
            profile_id=profile_id,
            user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if clients is None:
        raise HTTPException(status_code=404, detail="User or profile not found.")
    return [ClientResponse.model_validate(client) for client in clients]
