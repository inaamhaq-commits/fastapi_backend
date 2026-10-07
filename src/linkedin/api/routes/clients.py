from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from linkedin.api.deps import get_current_user, get_db
from linkedin.db.models.user import User
from linkedin.schemas.clients import ClientCreateRequest, ClientResponse, ClientUpdateRequest
from linkedin.services.clients import (
    create_client_profile,
    get_client_profile,
    list_client_profiles,
    update_client_profile,
)


router = APIRouter(prefix="/clients")


@router.get(
    "",
    response_model=list[ClientResponse],
    summary="List client profiles for your workspace",
)
def list_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClientResponse]:
    return [
        ClientResponse.model_validate(client)
        for client in list_client_profiles(db, current_user)
    ]


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new client profile for your workspace",
)
def create_client(
    payload: ClientCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientResponse:
    try:
        client = create_client_profile(db, payload, current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ClientResponse.model_validate(client)


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Get a client profile for your workspace",
)
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientResponse:
    client = get_client_profile(db, client_id=str(client_id), user=current_user)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found.")
    return ClientResponse.model_validate(client)


@router.patch(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Update a client profile for your workspace",
)
def update_client(
    client_id: UUID,
    payload: ClientUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientResponse:
    try:
        client = update_client_profile(
            db,
            client_id=str(client_id),
            payload=payload,
            user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found.")
    return ClientResponse.model_validate(client)
