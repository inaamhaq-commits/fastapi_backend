from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from linkedin.api.deps import get_current_user, get_db
from linkedin.db.models.user import User
from linkedin.schemas.clients import ClientResponse
from linkedin.schemas.user_profiles import (
    UserProfileCreateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from linkedin.services.clients import list_client_profiles_for_profile
from linkedin.services.user_profiles import (
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    update_profile,
)


router = APIRouter(prefix="/profiles")


@router.get(
    "",
    response_model=list[UserProfileResponse],
    summary="List your LinkedIn/source profiles",
)
def list_user_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserProfileResponse]:
    return [
        UserProfileResponse.model_validate(profile)
        for profile in list_profiles(db, current_user)
    ]


@router.post(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a LinkedIn/source profile",
)
def create_user_profile(
    payload: UserProfileCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    return UserProfileResponse.model_validate(
        create_profile(db, payload, current_user)
    )


@router.get(
    "/{profile_id}",
    response_model=UserProfileResponse,
    summary="Get one of your LinkedIn/source profiles",
)
def get_user_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    profile = get_profile(db, profile_id=str(profile_id), user=current_user)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return UserProfileResponse.model_validate(profile)


@router.get(
    "/{profile_id}/clients",
    response_model=list[ClientResponse],
    summary="List clients/prospects for a source profile",
)
def list_profile_clients(
    profile_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClientResponse]:
    try:
        clients = list_client_profiles_for_profile(
            db,
            profile_id=str(profile_id),
            user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if clients is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return [ClientResponse.model_validate(client) for client in clients]


@router.patch(
    "/{profile_id}",
    response_model=UserProfileResponse,
    summary="Update one of your LinkedIn/source profiles",
)
def update_user_profile(
    profile_id: UUID,
    payload: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    profile = update_profile(
        db,
        profile_id=str(profile_id),
        payload=payload,
        user=current_user,
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return UserProfileResponse.model_validate(profile)


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one of your LinkedIn/source profiles",
)
def delete_user_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    deleted = delete_profile(db, profile_id=str(profile_id), user=current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found.")
