from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from linkedin.api.deps import get_db
from linkedin.core.config import settings
from linkedin.schemas.auth import AuthSuccessResponse, LoginRequest, MessageResponse, SignUpRequest, TokenPairResponse
from linkedin.services.auth import (
    AuthConflictError,
    AuthCredentialsError,
    AuthTokenError,
    login_user,
    logout_user,
    refresh_user_session,
    register_user,
)


router = APIRouter(prefix="/auth")


def _set_auth_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.auth_access_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.auth_access_token_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.auth_refresh_token_days * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_access_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


@router.post(
    "/signup",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
def signup(
    payload: SignUpRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSuccessResponse:
    try:
        auth_response = register_user(db, payload)
    except AuthConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _set_auth_cookies(
        response,
        access_token=auth_response.access_token,
        refresh_token=auth_response.refresh_token,
    )
    return auth_response


@router.post(
    "/login",
    response_model=AuthSuccessResponse,
    summary="Log in a user",
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSuccessResponse:
    try:
        auth_response = login_user(db, payload)
    except AuthCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _set_auth_cookies(
        response,
        access_token=auth_response.access_token,
        refresh_token=auth_response.refresh_token,
    )
    return auth_response


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    summary="Refresh the authenticated session",
)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    try:
        token_pair = refresh_user_session(
            db,
            request.cookies.get(settings.auth_refresh_cookie_name),
        )
    except AuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _set_auth_cookies(
        response,
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
    )
    return token_pair


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out a user",
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> MessageResponse:
    logout_user(
        db,
        request.cookies.get(settings.auth_refresh_cookie_name),
    )
    _clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully.")
