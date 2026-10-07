import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from linkedin.core.security import create_jwt_token, decode_jwt_token, hash_password, verify_password
from linkedin.core.enums import UserRole
from linkedin.main import app
from linkedin.schemas.auth import AuthSuccessResponse, AuthUserResponse, LoginRequest, SignUpRequest, TokenPairResponse
from linkedin.services.auth import (
    AuthConflictError,
    AuthCredentialsError,
    AuthTokenError,
    login_user,
    logout_user,
    refresh_user_session,
    register_user,
)


class SecurityTests(unittest.TestCase):
    def test_hash_password_and_verify_password(self) -> None:
        password_hash = hash_password("super-secret-password")

        self.assertNotEqual(password_hash, "super-secret-password")
        self.assertTrue(verify_password("super-secret-password", password_hash))
        self.assertFalse(verify_password("wrong-password", password_hash))

    def test_create_and_decode_jwt_token(self) -> None:
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        token = create_jwt_token(
            subject="user-123",
            email="user@example.com",
            token_type="access",
            expires_at=expires_at,
        )

        payload = decode_jwt_token(token, expected_type="access")

        self.assertEqual(payload["sub"], "user-123")
        self.assertEqual(payload["email"], "user@example.com")
        self.assertEqual(payload["type"], "access")


class AuthServiceTests(unittest.TestCase):
    @patch("linkedin.services.auth.create_refresh_token")
    @patch("linkedin.services.auth.create_user")
    @patch("linkedin.services.auth.get_user_by_email")
    def test_register_user_hashes_password_and_issues_tokens(
        self,
        mock_get_user_by_email,
        mock_create_user,
        mock_create_refresh_token,
    ) -> None:
        db = Mock()
        mock_get_user_by_email.return_value = None
        created_user = SimpleNamespace(
            id="12345678-1234-5678-1234-567812345678",
            full_name="Inaam Ul Haq",
            email="inaam@example.com",
            role="user",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_create_user.return_value = created_user

        response = register_user(
            db,
            SignUpRequest(
                full_name="Inaam Ul Haq",
                email="inaam@example.com",
                password="super-secret-password",
            ),
        )

        self.assertEqual(response.user.email, "inaam@example.com")
        self.assertTrue(response.access_token)
        self.assertTrue(response.refresh_token)
        self.assertEqual(response.user.role, UserRole.USER)
        password_hash = mock_create_user.call_args.kwargs["password_hash"]
        self.assertNotEqual(password_hash, "super-secret-password")
        self.assertTrue(verify_password("super-secret-password", password_hash))
        self.assertEqual(mock_create_user.call_args.kwargs["role"], "user")
        mock_create_refresh_token.assert_called_once()

    @patch("linkedin.services.auth.create_refresh_token")
    @patch("linkedin.services.auth.create_user")
    @patch("linkedin.services.auth.get_user_by_email")
    def test_register_user_allows_manager_role(
        self,
        mock_get_user_by_email,
        mock_create_user,
        mock_create_refresh_token,
    ) -> None:
        db = Mock()
        mock_get_user_by_email.return_value = None
        created_user = SimpleNamespace(
            id="12345678-1234-5678-1234-567812345678",
            full_name="Ali",
            email="ali@invozone.com",
            role="manager",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_create_user.return_value = created_user

        response = register_user(
            db,
            SignUpRequest(
                full_name="Ali",
                email="ali@invozone.com",
                password="ali12345",
                role="manager",
            ),
        )

        self.assertEqual(response.user.role, UserRole.MANAGER)
        self.assertEqual(mock_create_user.call_args.kwargs["role"], "manager")
        mock_create_refresh_token.assert_called_once()

    @patch("linkedin.services.auth.get_user_by_email")
    def test_register_user_rejects_duplicate_email(self, mock_get_user_by_email) -> None:
        db = Mock()
        mock_get_user_by_email.return_value = SimpleNamespace(id="user-123")

        with self.assertRaises(AuthConflictError):
            register_user(
                db,
                SimpleNamespace(
                    full_name="Inaam Ul Haq",
                    email="inaam@example.com",
                    password="super-secret-password",
                ),
            )

    @patch("linkedin.services.auth.issue_token_pair")
    @patch("linkedin.services.auth.revoke_refresh_tokens_for_user")
    @patch("linkedin.services.auth.get_user_by_email")
    def test_login_user_rejects_invalid_password(
        self,
        mock_get_user_by_email,
        mock_revoke_refresh_tokens_for_user,
        mock_issue_token_pair,
    ) -> None:
        db = Mock()
        mock_get_user_by_email.return_value = SimpleNamespace(
            id="12345678-1234-5678-1234-567812345678",
            email="inaam@example.com",
            password_hash=hash_password("correct-password"),
        )

        with self.assertRaises(AuthCredentialsError):
            login_user(
                db,
                LoginRequest(email="inaam@example.com", password="wrong-password"),
            )

        mock_revoke_refresh_tokens_for_user.assert_not_called()
        mock_issue_token_pair.assert_not_called()

    @patch("linkedin.services.auth.create_refresh_token")
    @patch("linkedin.services.auth.revoke_refresh_token")
    @patch("linkedin.services.auth.get_refresh_token_by_hash")
    def test_refresh_user_session_rotates_refresh_token(
        self,
        mock_get_refresh_token_by_hash,
        mock_revoke_refresh_token,
        mock_create_refresh_token,
    ) -> None:
        db = Mock()
        refresh_token = create_jwt_token(
            subject="12345678-1234-5678-1234-567812345678",
            email="inaam@example.com",
            token_type="refresh",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        token_record = SimpleNamespace(
            user_id="12345678-1234-5678-1234-567812345678",
            revoked=False,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            user=SimpleNamespace(
                id="12345678-1234-5678-1234-567812345678",
                email="inaam@example.com",
                full_name="Inaam Ul Haq",
                role="user",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        )
        mock_get_refresh_token_by_hash.return_value = token_record

        token_pair = refresh_user_session(db, refresh_token)

        self.assertTrue(token_pair.access_token)
        self.assertTrue(token_pair.refresh_token)
        self.assertNotEqual(token_pair.refresh_token, refresh_token)
        mock_revoke_refresh_token.assert_called_once_with(db, token_record)
        mock_create_refresh_token.assert_called_once()

    @patch("linkedin.services.auth.get_refresh_token_by_hash")
    def test_refresh_user_session_rejects_unknown_token(self, mock_get_refresh_token_by_hash) -> None:
        db = Mock()
        refresh_token = create_jwt_token(
            subject="12345678-1234-5678-1234-567812345678",
            email="inaam@example.com",
            token_type="refresh",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        mock_get_refresh_token_by_hash.return_value = None

        with self.assertRaises(AuthTokenError):
            refresh_user_session(db, refresh_token)

    @patch("linkedin.services.auth.revoke_refresh_token")
    @patch("linkedin.services.auth.get_refresh_token_by_hash")
    def test_logout_user_revokes_refresh_token(
        self,
        mock_get_refresh_token_by_hash,
        mock_revoke_refresh_token,
    ) -> None:
        db = Mock()
        token_record = SimpleNamespace(revoked=False)
        mock_get_refresh_token_by_hash.return_value = token_record

        logout_user(db, "refresh-token")

        mock_revoke_refresh_token.assert_called_once_with(db, token_record)


class AuthRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user_response = AuthUserResponse(
            id="12345678-1234-5678-1234-567812345678",
            full_name="Inaam Ul Haq",
            email="inaam@example.com",
            role="user",
            created_at="2026-09-03T00:00:00Z",
            updated_at="2026-09-03T00:00:00Z",
        )

    @patch("linkedin.api.routes.auth.register_user")
    def test_signup_sets_auth_cookies(self, mock_register_user) -> None:
        mock_register_user.return_value = AuthSuccessResponse(
            user=self.user_response,
            access_token="access-123",
            refresh_token="refresh-123",
        )

        response = self.client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Inaam Ul Haq",
                "email": "inaam@example.com",
                "password": "super-secret-password",
            },
        )

        self.assertEqual(response.status_code, 201)
        set_cookie = ",".join(response.headers.get_list("set-cookie"))
        self.assertIn("access_token=access-123", set_cookie)
        self.assertIn("refresh_token=refresh-123", set_cookie)
        self.assertIn("HttpOnly", set_cookie)

    @patch("linkedin.api.routes.auth.register_user")
    def test_signup_returns_conflict_for_duplicate_email(self, mock_register_user) -> None:
        mock_register_user.side_effect = AuthConflictError("A user with this email already exists.")

        response = self.client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Inaam Ul Haq",
                "email": "inaam@example.com",
                "password": "super-secret-password",
            },
        )

        self.assertEqual(response.status_code, 409)

    @patch("linkedin.api.routes.auth.login_user")
    def test_login_sets_auth_cookies(self, mock_login_user) -> None:
        mock_login_user.return_value = AuthSuccessResponse(
            user=self.user_response,
            access_token="access-123",
            refresh_token="refresh-123",
        )

        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "inaam@example.com",
                "password": "super-secret-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        set_cookie = ",".join(response.headers.get_list("set-cookie"))
        self.assertIn("access_token=access-123", set_cookie)
        self.assertIn("refresh_token=refresh-123", set_cookie)

    @patch("linkedin.api.routes.auth.login_user")
    def test_login_returns_unauthorized_for_invalid_credentials(self, mock_login_user) -> None:
        mock_login_user.side_effect = AuthCredentialsError("Invalid email or password.")

        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "inaam@example.com",
                "password": "wrong-password",
            },
        )

        self.assertEqual(response.status_code, 401)

    @patch("linkedin.api.routes.auth.refresh_user_session")
    def test_refresh_rotates_auth_cookies(self, mock_refresh_user_session) -> None:
        mock_refresh_user_session.return_value = TokenPairResponse(
            access_token="access-456",
            refresh_token="refresh-456",
        )

        response = self.client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "refresh-123"},
        )

        self.assertEqual(response.status_code, 200)
        set_cookie = ",".join(response.headers.get_list("set-cookie"))
        self.assertIn("access_token=access-456", set_cookie)
        self.assertIn("refresh_token=refresh-456", set_cookie)

    @patch("linkedin.api.routes.auth.refresh_user_session")
    def test_refresh_returns_unauthorized_for_missing_or_invalid_token(
        self,
        mock_refresh_user_session,
    ) -> None:
        mock_refresh_user_session.side_effect = AuthTokenError("Refresh token is invalid.")

        response = self.client.post("/api/v1/auth/refresh")

        self.assertEqual(response.status_code, 401)

    @patch("linkedin.api.routes.auth.logout_user")
    def test_logout_clears_auth_cookies(self, mock_logout_user) -> None:
        response = self.client.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": "refresh-123"},
        )

        self.assertEqual(response.status_code, 200)
        set_cookie = ",".join(response.headers.get_list("set-cookie"))
        self.assertIn("access_token=\"\"", set_cookie)
        self.assertIn("refresh_token=\"\"", set_cookie)
        mock_logout_user.assert_called_once()
