from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from linkedin.core.enums import UserRole
from linkedin.core.security import hash_password
from linkedin.db.models.user import User
from linkedin.repositories.users import upsert_manager_user


def seed_default_user_roles(db: Session) -> User:
    db.execute(
        text("UPDATE users SET role = :role WHERE role IS NULL"),
        {"role": UserRole.USER.value},
    )
    return upsert_manager_user(
        db,
        full_name="Ali",
        email="ali@invozone.com",
        password_hash=hash_password("ali12345"),
    )
