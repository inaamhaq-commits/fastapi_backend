import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from linkedin.main import app
from linkedin.schemas.clients import ClientCreateRequest, ClientUpdateRequest
from linkedin.services.clients import (
    create_client_profile,
    get_client_profile,
    list_manager_client_profiles,
    list_manager_client_profiles_for_user,
    list_manager_users_with_client_counts,
    list_client_profiles,
    update_client_profile,
)


def client_stage_defaults() -> dict[str, bool]:
    return {
        "calls_scheduled": False,
        "qualified": False,
        "pre_sale": False,
        "not_a_fit": False,
    }


class ClientServiceTests(unittest.TestCase):
    @patch("linkedin.services.clients.create_client")
    def test_create_client_profile_uses_authenticated_user_id(self, mock_create_client) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        payload = ClientCreateRequest(
            name="Sarah Lee",
            company="Acme Inc",
            email="Sarah@Example.com",
            phone="+1 555 0100",
            linkedin_url="https://www.linkedin.com/in/sarah-lee/",
            notes="Warm intro from last campaign.",
            score=72,
            calls_scheduled=True,
        )
        mock_create_client.return_value = SimpleNamespace()

        create_client_profile(db, payload, user)

        mock_create_client.assert_called_once_with(
            db,
            user_id="12345678-1234-5678-1234-567812345678",
            profile_id=None,
            name="Sarah Lee",
            company="Acme Inc",
            email="Sarah@example.com",
            phone="+1 555 0100",
            linkedin_url="https://www.linkedin.com/in/sarah-lee/",
            notes="Warm intro from last campaign.",
            score=72,
            calls_scheduled=True,
            qualified=False,
            pre_sale=False,
            not_a_fit=False,
        )

    @patch("linkedin.services.clients.list_clients_for_user")
    def test_list_client_profiles_uses_authenticated_user_id(self, mock_list_clients_for_user) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_list_clients_for_user.return_value = []

        clients = list_client_profiles(db, user)

        self.assertEqual(clients, [])
        mock_list_clients_for_user.assert_called_once_with(
            db,
            user_id="12345678-1234-5678-1234-567812345678",
        )

    @patch("linkedin.services.clients.list_all_clients")
    def test_list_manager_client_profiles_allows_manager(
        self,
        mock_list_all_clients,
    ) -> None:
        db = Mock()
        manager = SimpleNamespace(id="manager-user-id", role="manager")
        mock_list_all_clients.return_value = []

        clients = list_manager_client_profiles(db, manager)

        self.assertEqual(clients, [])
        mock_list_all_clients.assert_called_once_with(db)

    def test_list_manager_client_profiles_rejects_regular_user(self) -> None:
        db = Mock()
        user = SimpleNamespace(id="regular-user-id", role="user")

        with self.assertRaises(PermissionError):
            list_manager_client_profiles(db, user)

    @patch("linkedin.services.clients.list_users_with_client_counts")
    def test_list_manager_users_with_client_counts_allows_manager(
        self,
        mock_list_users_with_client_counts,
    ) -> None:
        db = Mock()
        manager = SimpleNamespace(id="manager-user-id", role="manager")
        mock_list_users_with_client_counts.return_value = [
            {
                "user_id": "talha_user_id",
                "name": "Talha",
                "email": "talha@example.com",
                "clients_count": 42,
            }
        ]

        users = list_manager_users_with_client_counts(db, manager)

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].clients_count, 42)
        mock_list_users_with_client_counts.assert_called_once_with(db)

    @patch("linkedin.services.clients.list_clients_by_user_id")
    @patch("linkedin.services.clients.get_user_by_id")
    def test_list_manager_client_profiles_for_user_allows_manager(
        self,
        mock_get_user_by_id,
        mock_list_clients_by_user_id,
    ) -> None:
        db = Mock()
        manager = SimpleNamespace(id="manager-user-id", role="manager")
        mock_get_user_by_id.return_value = SimpleNamespace(id="target-user-id")
        mock_list_clients_by_user_id.return_value = []

        clients = list_manager_client_profiles_for_user(
            db,
            target_user_id="target-user-id",
            user=manager,
        )

        self.assertEqual(clients, [])
        mock_get_user_by_id.assert_called_once_with(db, "target-user-id")
        mock_list_clients_by_user_id.assert_called_once_with(
            db,
            user_id="target-user-id",
        )

    @patch("linkedin.services.clients.get_user_by_id")
    def test_list_manager_client_profiles_for_user_returns_none_for_missing_user(
        self,
        mock_get_user_by_id,
    ) -> None:
        db = Mock()
        manager = SimpleNamespace(id="manager-user-id", role="manager")
        mock_get_user_by_id.return_value = None

        clients = list_manager_client_profiles_for_user(
            db,
            target_user_id="missing-user-id",
            user=manager,
        )

        self.assertIsNone(clients)

    @patch("linkedin.services.clients.get_client_for_user")
    def test_get_client_profile_uses_authenticated_user_id(self, mock_get_client_for_user) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_get_client_for_user.return_value = SimpleNamespace()

        get_client_profile(
            db,
            client_id="87654321-4321-6789-4321-678987654321",
            user=user,
        )

        mock_get_client_for_user.assert_called_once_with(
            db,
            client_id="87654321-4321-6789-4321-678987654321",
            user_id="12345678-1234-5678-1234-567812345678",
        )

    @patch("linkedin.services.clients.create_client")
    def test_create_client_profile_allows_blank_optional_fields(self, mock_create_client) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        payload = ClientCreateRequest(
            name="Sarah Lee",
            company="Acme Inc",
            email="",
            phone="",
            linkedin_url="",
            notes="",
        )
        mock_create_client.return_value = SimpleNamespace()

        create_client_profile(db, payload, user)

        mock_create_client.assert_called_once_with(
            db,
            user_id="12345678-1234-5678-1234-567812345678",
            profile_id=None,
            name="Sarah Lee",
            company="Acme Inc",
            email=None,
            phone=None,
            linkedin_url=None,
            notes=None,
            score=0,
            calls_scheduled=False,
            qualified=False,
            pre_sale=False,
            not_a_fit=False,
        )

    @patch("linkedin.services.clients.update_client")
    @patch("linkedin.services.clients.get_profile_for_user")
    @patch("linkedin.services.clients.get_client_for_user")
    def test_update_client_profile_updates_score(
        self,
        mock_get_client_for_user,
        mock_get_profile_for_user,
        mock_update_client,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        client = SimpleNamespace()
        mock_get_client_for_user.return_value = client
        mock_get_profile_for_user.return_value = None
        mock_update_client.return_value = client

        updated = update_client_profile(
            db,
            client_id="87654321-4321-6789-4321-678987654321",
            payload=ClientUpdateRequest(score=88),
            user=user,
        )

        self.assertIs(updated, client)
        mock_get_client_for_user.assert_called_once_with(
            db,
            client_id="87654321-4321-6789-4321-678987654321",
            user_id="12345678-1234-5678-1234-567812345678",
        )
        mock_update_client.assert_called_once_with(client, {"score": 88})

    @patch("linkedin.services.clients.update_client")
    @patch("linkedin.services.clients.get_profile_for_user")
    @patch("linkedin.services.clients.get_client_for_user")
    def test_update_client_profile_keeps_one_stage_true(
        self,
        mock_get_client_for_user,
        mock_get_profile_for_user,
        mock_update_client,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        client = SimpleNamespace()
        mock_get_client_for_user.return_value = client
        mock_get_profile_for_user.return_value = None
        mock_update_client.return_value = client

        update_client_profile(
            db,
            client_id="87654321-4321-6789-4321-678987654321",
            payload=ClientUpdateRequest(qualified=True),
            user=user,
        )

        mock_update_client.assert_called_once_with(
            client,
            {
                "calls_scheduled": False,
                "qualified": True,
                "pre_sale": False,
                "not_a_fit": False,
            },
        )

    @patch("linkedin.services.clients.create_client")
    @patch("linkedin.services.clients.get_profile_for_user")
    def test_create_client_profile_accepts_owned_profile(
        self,
        mock_get_profile_for_user,
        mock_create_client,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        profile_id = "11111111-1111-1111-1111-111111111111"
        mock_get_profile_for_user.return_value = SimpleNamespace(id=profile_id)
        mock_create_client.return_value = SimpleNamespace()

        create_client_profile(
            db,
            ClientCreateRequest(
                profile_id=profile_id,
                name="Sarah Lee",
                company="Acme Inc",
            ),
            user,
        )

        mock_get_profile_for_user.assert_called_once_with(
            db,
            profile_id=profile_id,
            user_id=user.id,
        )
        self.assertEqual(mock_create_client.call_args.kwargs["profile_id"], profile_id)

    @patch("linkedin.services.clients.get_profile_for_user")
    def test_create_client_profile_rejects_unowned_profile(
        self,
        mock_get_profile_for_user,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_get_profile_for_user.return_value = None

        with self.assertRaises(PermissionError):
            create_client_profile(
                db,
                ClientCreateRequest(
                    profile_id="11111111-1111-1111-1111-111111111111",
                    name="Sarah Lee",
                    company="Acme Inc",
                ),
                user,
            )

    def test_client_create_rejects_multiple_true_stages(self) -> None:
        with self.assertRaises(ValueError):
            ClientCreateRequest(
                name="Sarah Lee",
                company="Acme Inc",
                calls_scheduled=True,
                qualified=True,
            )

    def test_client_update_rejects_multiple_true_stages(self) -> None:
        with self.assertRaises(ValueError):
            ClientUpdateRequest(pre_sale=True, not_a_fit=True)


class ClientRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_list_clients_route_supports_cors_preflight(self) -> None:
        response = self.client.options(
            "/api/v1/clients",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )

    def test_list_clients_auth_error_includes_cors_header(self) -> None:
        response = self.client.get(
            "/api/v1/clients",
            headers={"Origin": "http://localhost:3000"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )

    @patch("linkedin.api.routes.clients.list_client_profiles")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_list_clients_requires_auth_and_returns_only_user_clients(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_list_client_profiles,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        now = datetime.now(UTC)
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_list_client_profiles.return_value = [
            SimpleNamespace(
                id="87654321-4321-6789-4321-678987654321",
                user_id=user.id,
                profile_id=None,
                name="Sarah Lee",
                company="Acme Inc",
                email="sarah@example.com",
                phone="+1 555 0100",
                linkedin_url="https://www.linkedin.com/in/sarah-lee/",
                notes="Warm intro from last campaign.",
                score=0,
                **client_stage_defaults(),
                needs_follow_up=False,
                is_active=True,
                status="new",
                created_at=now,
                updated_at=now,
            )
        ]

        response = self.client.get(
            "/api/v1/clients",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["user_id"], user.id)
        self.assertEqual(body[0]["name"], "Sarah Lee")
        mock_list_client_profiles.assert_called_once()

    @patch("linkedin.api.routes.manager.list_manager_client_profiles")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_manager_can_list_all_clients(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_list_manager_client_profiles,
    ) -> None:
        manager = SimpleNamespace(id="manager-user-id", role="manager")
        now = datetime.now(UTC)
        mock_decode_jwt_token.return_value = {"sub": manager.id}
        mock_get_user_by_id.return_value = manager
        mock_list_manager_client_profiles.return_value = [
            SimpleNamespace(
                id="87654321-4321-6789-4321-678987654321",
                user_id="12345678-1234-5678-1234-567812345678",
                profile_id=None,
                name="Sarah Lee",
                company="Acme Inc",
                email="sarah@example.com",
                phone="+1 555 0100",
                linkedin_url="https://www.linkedin.com/in/sarah-lee/",
                notes="Warm intro from last campaign.",
                score=81,
                calls_scheduled=False,
                qualified=True,
                pre_sale=False,
                not_a_fit=False,
                needs_follow_up=False,
                is_active=True,
                status="new",
                created_at=now,
                updated_at=now,
            )
        ]

        response = self.client.get(
            "/api/v1/manager/clients",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["user_id"], "12345678-1234-5678-1234-567812345678")
        self.assertEqual(body[0]["qualified"], True)
        mock_list_manager_client_profiles.assert_called_once()

    @patch("linkedin.api.routes.manager.list_manager_client_profiles")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_regular_user_cannot_list_manager_clients(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_list_manager_client_profiles,
    ) -> None:
        user = SimpleNamespace(id="regular-user-id", role="user")
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_list_manager_client_profiles.side_effect = PermissionError(
            "Manager access required."
        )

        response = self.client.get(
            "/api/v1/manager/clients",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 403)

    @patch("linkedin.api.routes.manager.list_manager_users_with_client_counts")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_manager_can_list_users_with_client_counts(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_list_manager_users_with_client_counts,
    ) -> None:
        manager = SimpleNamespace(id="manager-user-id", role="manager")
        mock_decode_jwt_token.return_value = {"sub": manager.id}
        mock_get_user_by_id.return_value = manager
        mock_list_manager_users_with_client_counts.return_value = [
            {
                "user_id": "talha_user_id",
                "name": "Talha",
                "email": "talha@example.com",
                "clients_count": 42,
            }
        ]

        response = self.client.get(
            "/api/v1/manager/users",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "Talha")
        self.assertEqual(response.json()[0]["clients_count"], 42)

    @patch("linkedin.api.routes.manager.list_manager_client_profiles_for_user")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_manager_can_list_clients_for_user(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_list_manager_client_profiles_for_user,
    ) -> None:
        manager = SimpleNamespace(id="manager-user-id", role="manager")
        now = datetime.now(UTC)
        mock_decode_jwt_token.return_value = {"sub": manager.id}
        mock_get_user_by_id.return_value = manager
        mock_list_manager_client_profiles_for_user.return_value = [
            SimpleNamespace(
                id="87654321-4321-6789-4321-678987654321",
                user_id="12345678-1234-5678-1234-567812345678",
                profile_id=None,
                name="Sarah Lee",
                company="Acme Inc",
                email="sarah@example.com",
                phone="+1 555 0100",
                linkedin_url="https://www.linkedin.com/in/sarah-lee/",
                notes="Warm intro from last campaign.",
                score=81,
                calls_scheduled=False,
                qualified=True,
                pre_sale=False,
                not_a_fit=False,
                needs_follow_up=False,
                is_active=True,
                status="new",
                created_at=now,
                updated_at=now,
            )
        ]

        response = self.client.get(
            "/api/v1/manager/users/12345678-1234-5678-1234-567812345678/clients",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()[0]["user_id"],
            "12345678-1234-5678-1234-567812345678",
        )
        mock_list_manager_client_profiles_for_user.assert_called_once()

    @patch("linkedin.api.routes.manager.list_manager_client_profiles_for_user")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_manager_user_clients_returns_404_for_missing_user(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_list_manager_client_profiles_for_user,
    ) -> None:
        manager = SimpleNamespace(id="manager-user-id", role="manager")
        mock_decode_jwt_token.return_value = {"sub": manager.id}
        mock_get_user_by_id.return_value = manager
        mock_list_manager_client_profiles_for_user.return_value = None

        response = self.client.get(
            "/api/v1/manager/users/missing-user-id/clients",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 404)

    @patch("linkedin.api.routes.clients.create_client_profile")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_create_client_requires_auth_and_returns_created_client(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_create_client_profile,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        now = datetime.now(UTC)
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_create_client_profile.return_value = SimpleNamespace(
            id="87654321-4321-6789-4321-678987654321",
            user_id=user.id,
            profile_id=None,
            name="Sarah Lee",
            company="Acme Inc",
            email="sarah@example.com",
            phone="+1 555 0100",
            linkedin_url="https://www.linkedin.com/in/sarah-lee/",
            notes="Warm intro from last campaign.",
            score=64,
            calls_scheduled=False,
            qualified=True,
            pre_sale=False,
            not_a_fit=False,
            needs_follow_up=False,
            is_active=True,
            status="new",
            created_at=now,
            updated_at=now,
        )

        response = self.client.post(
            "/api/v1/clients",
            cookies={"access_token": "access-123"},
            json={
                "name": "Sarah Lee",
                "company": "Acme Inc",
                "email": "sarah@example.com",
                "phone": "+1 555 0100",
                "linkedin_url": "https://www.linkedin.com/in/sarah-lee/",
                "notes": "Warm intro from last campaign.",
                "score": 64,
                "qualified": True,
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["user_id"], user.id)
        self.assertEqual(body["score"], 64)
        self.assertTrue(body["qualified"])
        self.assertFalse(body["calls_scheduled"])
        self.assertFalse(body["needs_follow_up"])
        self.assertTrue(body["is_active"])
        self.assertEqual(body["status"], "new")
        self.assertEqual(mock_create_client_profile.call_args.args[1].score, 64)

    @patch("linkedin.api.routes.clients.update_client_profile")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_update_client_allows_score_change(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_update_client_profile,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        now = datetime.now(UTC)
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_update_client_profile.return_value = SimpleNamespace(
            id="87654321-4321-6789-4321-678987654321",
            user_id=user.id,
            profile_id=None,
            name="Sarah Lee",
            company="Acme Inc",
            email="sarah@example.com",
            phone="+1 555 0100",
            linkedin_url="https://www.linkedin.com/in/sarah-lee/",
            notes="Warm intro from last campaign.",
            score=88,
            calls_scheduled=False,
            qualified=True,
            pre_sale=False,
            not_a_fit=False,
            needs_follow_up=False,
            is_active=True,
            status="new",
            created_at=now,
            updated_at=now,
        )

        response = self.client.patch(
            "/api/v1/clients/87654321-4321-6789-4321-678987654321",
            cookies={"access_token": "access-123"},
            json={"score": 88, "qualified": True},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["score"], 88)
        self.assertTrue(body["qualified"])
        mock_update_client_profile.assert_called_once()

    @patch("linkedin.api.routes.clients.get_client_profile")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_get_client_by_id_requires_auth_and_returns_user_client(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_get_client_profile,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        now = datetime.now(UTC)
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_get_client_profile.return_value = SimpleNamespace(
            id="87654321-4321-6789-4321-678987654321",
            user_id=user.id,
            profile_id=None,
            name="Sarah Lee",
            company="Acme Inc",
            email="sarah@example.com",
            phone="+1 555 0100",
                linkedin_url="https://www.linkedin.com/in/sarah-lee/",
                notes="Warm intro from last campaign.",
                score=0,
                **client_stage_defaults(),
                needs_follow_up=False,
            is_active=True,
            status="new",
            created_at=now,
            updated_at=now,
        )

        response = self.client.get(
            "/api/v1/clients/87654321-4321-6789-4321-678987654321",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["id"], "87654321-4321-6789-4321-678987654321")
        self.assertEqual(body["name"], "Sarah Lee")
        mock_get_client_profile.assert_called_once()

    @patch("linkedin.api.routes.profiles.list_client_profiles_for_profile")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_profile_clients_route_loads_clients_by_profile_id(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_list_client_profiles_for_profile,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678", role="user")
        profile_id = "171abd5c-2d0e-432a-a58e-8b76364a4b09"
        now = datetime.now(UTC)
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_list_client_profiles_for_profile.return_value = [
            SimpleNamespace(
                id="87654321-4321-6789-4321-678987654321",
                user_id=user.id,
                profile_id=profile_id,
                name="Sarah Lee",
                company="Acme Inc",
                email="sarah@example.com",
                phone="+1 555 0100",
                linkedin_url="https://www.linkedin.com/in/sarah-lee/",
                notes="Warm intro from last campaign.",
                score=0,
                **client_stage_defaults(),
                needs_follow_up=False,
                is_active=True,
                status="new",
                created_at=now,
                updated_at=now,
            )
        ]

        response = self.client.get(
            f"/api/v1/profiles/{profile_id}/clients",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["profile_id"], profile_id)
        mock_list_client_profiles_for_profile.assert_called_once()

    @patch("linkedin.api.routes.clients.get_client_profile")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_get_client_by_id_returns_404_when_missing(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_get_client_profile,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_get_client_profile.return_value = None

        response = self.client.get(
            "/api/v1/clients/87654321-4321-6789-4321-678987654321",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 404)

    def test_create_client_rejects_missing_access_token(self) -> None:
        response = self.client.post(
            "/api/v1/clients",
            json={
                "name": "Sarah Lee",
                "company": "Acme Inc",
                "email": "",
                "phone": "",
                "linkedin_url": "",
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_list_clients_rejects_missing_access_token(self) -> None:
        response = self.client.get("/api/v1/clients")

        self.assertEqual(response.status_code, 401)

    @patch("linkedin.api.routes.clients.list_client_profiles")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_list_clients_accepts_bearer_access_token(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_list_client_profiles,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_list_client_profiles.return_value = []

        response = self.client.get(
            "/api/v1/clients",
            headers={"Authorization": "Bearer access-123"},
        )

        self.assertEqual(response.status_code, 200)
        mock_decode_jwt_token.assert_called_once_with(
            "access-123",
            expected_type="access",
        )
