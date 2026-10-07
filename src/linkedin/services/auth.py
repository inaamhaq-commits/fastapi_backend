from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from linkedin.core.config import settings
from linkedin.core.security import (
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    hash_token,
    verify_password,
)
from linkedin.db.models.user import User
from linkedin.repositories.refresh_tokens import (
    create_refresh_token,
    get_refresh_token_by_hash,
    revoke_refresh_token,
    revoke_refresh_tokens_for_user,
)
from linkedin.repositories.users import create_user, get_user_by_email
from linkedin.schemas.auth import AuthSuccessResponse, AuthUserResponse, LoginRequest, SignUpRequest, TokenPairResponse


class AuthConflictError(Exception):
    pass


class AuthCredentialsError(Exception):
    pass


class AuthTokenError(Exception):
    pass


@dataclass(slots=True)
class IssuedTokenPair:
    access_token: str
    refresh_token: str


def _build_auth_success_response(user: User, tokens: IssuedTokenPair) -> AuthSuccessResponse:
    return AuthSuccessResponse(
        user=AuthUserResponse.model_validate(user),
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


def issue_token_pair(db: Session, user: User) -> IssuedTokenPair:
    now = datetime.now(UTC)
    access_expires_at = now + timedelta(minutes=settings.auth_access_token_minutes)
    refresh_expires_at = now + timedelta(days=settings.auth_refresh_token_days)

    access_token = create_jwt_token(
        subject=user.id,
        email=user.email,
        token_type="access",
        expires_at=access_expires_at,
    )
    refresh_token = create_jwt_token(
        subject=user.id,
        email=user.email,
        token_type="refresh",
        expires_at=refresh_expires_at,
    )

    create_refresh_token(
        db,
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_expires_at,
    )
    return IssuedTokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def register_user(db: Session, payload: SignUpRequest) -> AuthSuccessResponse:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise AuthConflictError("A user with this email already exists.")

    user = create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
    )
    tokens = issue_token_pair(db, user)
    return _build_auth_success_response(user, tokens)


def login_user(db: Session, payload: LoginRequest) -> AuthSuccessResponse:
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthCredentialsError("Invalid email or password.")

    revoke_refresh_tokens_for_user(db, user.id)
    tokens = issue_token_pair(db, user)
    return _build_auth_success_response(user, tokens)


def refresh_user_session(db: Session, refresh_token: str | None) -> TokenPairResponse:
    if not refresh_token:
        raise AuthTokenError("Refresh token is missing.")

    try:
        payload = decode_jwt_token(refresh_token, expected_type="refresh")
    except ValueError as exc:
        raise AuthTokenError(str(exc)) from exc

    token_record = get_refresh_token_by_hash(db, hash_token(refresh_token))
    if token_record is None or token_record.revoked:
        raise AuthTokenError("Refresh token is invalid.")
    if token_record.expires_at <= datetime.now(UTC):
        raise AuthTokenError("Refresh token has expired.")

    user_id = str(payload["sub"])
    if token_record.user_id != user_id:
        raise AuthTokenError("Refresh token user mismatch.")

    user = token_record.user
    if user is None:
        raise AuthTokenError("User not found for refresh token.")

    revoke_refresh_token(db, token_record)
    tokens = issue_token_pair(db, user)
    return TokenPairResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


def logout_user(db: Session, refresh_token: str | None) -> None:
    if not refresh_token:
        return

    token_record = get_refresh_token_by_hash(db, hash_token(refresh_token))
    if token_record is None or token_record.revoked:
        return
    revoke_refresh_token(db, token_record)
