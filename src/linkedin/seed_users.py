from __future__ import annotations

from linkedin.db.session import get_session_factory
from linkedin.services.users import seed_default_user_roles


def main() -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        manager = seed_default_user_roles(db)
        print(f"Manager user ready: {manager.email} ({manager.role})")


if __name__ == "__main__":
    main()
