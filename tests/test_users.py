import unittest
from unittest.mock import Mock, patch

from linkedin.services.users import seed_default_user_roles


class UserServiceTests(unittest.TestCase):
    @patch("linkedin.services.users.hash_password")
    @patch("linkedin.services.users.upsert_manager_user")
    def test_seed_default_user_roles_marks_existing_users_and_creates_manager(
        self,
        mock_upsert_manager_user,
        mock_hash_password,
    ) -> None:
        db = Mock()
        mock_hash_password.return_value = "hashed-password"

        seed_default_user_roles(db)

        db.execute.assert_called_once()
        statement = str(db.execute.call_args.args[0])
        self.assertIn("UPDATE users SET role = :role WHERE role IS NULL", statement)
        self.assertEqual(db.execute.call_args.args[1], {"role": "user"})
        mock_upsert_manager_user.assert_called_once_with(
            db,
            full_name="Ali",
            email="ali@invozone.com",
            password_hash="hashed-password",
        )


if __name__ == "__main__":
    unittest.main()
