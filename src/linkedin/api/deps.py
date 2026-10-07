from collections.abc import Generator

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from linkedin.core.config import settings
from linkedin.core.security import decode_jwt_token
from linkedin.db.session import get_db_session
from linkedin.repositories.users import get_user_by_id


def get_db() -> Generator[Any, None, None]:
    yield from get_db_session()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    access_token = request.cookies.get(settings.auth_access_cookie_name)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        token_payload = decode_jwt_token(access_token, expected_type="access")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    user = get_user_by_id(db, str(token_payload["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found.",
        )
    return user
