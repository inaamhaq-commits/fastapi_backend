import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from linkedin.main import app
from linkedin.repositories.user_profiles import delete_user_profile
from linkedin.services.user_profiles import delete_profile


class UserProfileRepositoryTests(unittest.TestCase):
    @patch("linkedin.repositories.user_profiles.object_session")
    def test_delete_user_profile_deletes_and_commits(self, mock_object_session) -> None:
        db = Mock()
        profile = SimpleNamespace(id="11111111-1111-1111-1111-111111111111")
        mock_object_session.return_value = db

        delete_user_profile(profile)

        db.delete.assert_called_once_with(profile)
        db.commit.assert_called_once_with()


class UserProfileServiceTests(unittest.TestCase):
    @patch("linkedin.services.user_profiles.delete_user_profile")
    @patch("linkedin.services.user_profiles.get_profile_for_user")
    def test_delete_profile_deletes_owned_profile(
        self,
        mock_get_profile_for_user,
        mock_delete_user_profile,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        profile = SimpleNamespace(id="11111111-1111-1111-1111-111111111111")
        mock_get_profile_for_user.return_value = profile

        deleted = delete_profile(db, profile_id=profile.id, user=user)

        self.assertTrue(deleted)
        mock_get_profile_for_user.assert_called_once_with(
            db,
            profile_id=profile.id,
            user_id=user.id,
        )
        mock_delete_user_profile.assert_called_once_with(profile)

    @patch("linkedin.services.user_profiles.delete_user_profile")
    @patch("linkedin.services.user_profiles.get_profile_for_user")
    def test_delete_profile_returns_false_for_missing_profile(
        self,
        mock_get_profile_for_user,
        mock_delete_user_profile,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_get_profile_for_user.return_value = None

        deleted = delete_profile(
            db,
            profile_id="11111111-1111-1111-1111-111111111111",
            user=user,
        )

        self.assertFalse(deleted)
        mock_delete_user_profile.assert_not_called()


class UserProfileRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("linkedin.api.routes.profiles.delete_profile")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_delete_profile_route_returns_no_content(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_delete_profile,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        profile_id = "11111111-1111-1111-1111-111111111111"
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_delete_profile.return_value = True

        response = self.client.delete(
            f"/api/v1/profiles/{profile_id}",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        mock_delete_profile.assert_called_once()

    @patch("linkedin.api.routes.profiles.delete_profile")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_delete_profile_route_returns_404_for_missing_profile(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_delete_profile,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        profile_id = "11111111-1111-1111-1111-111111111111"
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_delete_profile.return_value = False

        response = self.client.delete(
            f"/api/v1/profiles/{profile_id}",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Profile not found.")


if __name__ == "__main__":
    unittest.main()
