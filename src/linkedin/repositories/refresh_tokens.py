from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from linkedin.db.models.refresh_token import RefreshToken


def create_refresh_token(
    db: Session,
    *,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    return refresh_token


def get_refresh_token_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    return db.scalar(statement)


def revoke_refresh_token(db: Session, refresh_token: RefreshToken) -> None:
    refresh_token.revoked = True
    db.commit()


def revoke_refresh_tokens_for_user(db: Session, user_id: str) -> None:
    statement = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked.is_(False),
    )
    for refresh_token in db.scalars(statement):
        refresh_token.revoked = True
    db.commit()
