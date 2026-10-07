import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from linkedin.main import app
from linkedin.schemas.dashboard import DashboardOverviewResponse
from linkedin.services.dashboard import (
    ManagerPermissionError,
    get_dashboard_overview,
    get_manager_dashboard,
)


class DashboardServiceTests(unittest.TestCase):
    @patch("linkedin.services.dashboard.get_client_overview_counts")
    def test_get_dashboard_overview_uses_requested_range(
        self,
        mock_get_client_overview_counts,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_get_client_overview_counts.return_value = {
            "leads_generated": 74,
            "calls_scheduled": 46,
            "qualified": 31,
            "pre_sale": 19,
            "not_a_fit": 13,
        }

        overview = get_dashboard_overview(db, range_name="month", user=user)

        self.assertEqual(overview.label, "This Month")
        self.assertEqual(overview.leads_generated, 74)
        self.assertEqual(overview.calls_scheduled, 46)
        self.assertEqual(overview.qualified, 31)
        self.assertEqual(overview.pre_sale, 19)
        self.assertEqual(overview.not_a_fit, 13)
        mock_get_client_overview_counts.assert_called_once()
        self.assertEqual(mock_get_client_overview_counts.call_args.kwargs["user_id"], user.id)

    @patch("linkedin.services.dashboard.list_user_lead_counts")
    def test_get_manager_dashboard_returns_totals_and_users(
        self,
        mock_list_user_lead_counts,
    ) -> None:
        db = Mock()
        manager = SimpleNamespace(
            id="manager-user-id",
            role="manager",
        )
        mock_list_user_lead_counts.return_value = [
            {
                "user_id": "talha_user_id",
                "name": "Talha",
                "email": "talha@example.com",
                "total_leads": 42,
                "calls_scheduled": 15,
                "qualified": 12,
                "pre_sale": 7,
                "not_a_fit": 5,
            },
            {
                "user_id": "ali_user_id",
                "name": "Ali",
                "email": "ali@example.com",
                "total_leads": 78,
                "calls_scheduled": 29,
                "qualified": 26,
                "pre_sale": 14,
                "not_a_fit": 12,
            },
        ]

        dashboard = get_manager_dashboard(db, user=manager)

        self.assertEqual(dashboard.totals.total_leads, 120)
        self.assertEqual(dashboard.totals.calls_scheduled, 44)
        self.assertEqual(dashboard.totals.qualified, 38)
        self.assertEqual(dashboard.totals.pre_sale, 21)
        self.assertEqual(dashboard.totals.not_a_fit, 17)
        self.assertEqual(len(dashboard.users), 2)
        self.assertEqual(dashboard.users[0].user_id, "talha_user_id")

    def test_get_manager_dashboard_rejects_regular_user(self) -> None:
        db = Mock()
        user = SimpleNamespace(role="user")

        with self.assertRaises(ManagerPermissionError):
            get_manager_dashboard(db, user=user)


class DashboardRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("linkedin.api.routes.dashboard.get_dashboard_overview")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_get_dashboard_overview_returns_counts(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_get_dashboard_overview,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_get_dashboard_overview.return_value = DashboardOverviewResponse(
            label="This Month",
            leads_generated=74,
            calls_scheduled=46,
            qualified=31,
            pre_sale=19,
            not_a_fit=13,
        )

        response = self.client.get(
            "/api/v1/dashboard/overview?range=month",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "label": "This Month",
                "leads_generated": 74,
                "calls_scheduled": 46,
                "qualified": 31,
                "pre_sale": 19,
                "not_a_fit": 13,
            },
        )
        mock_get_dashboard_overview.assert_called_once()
        self.assertEqual(
            mock_get_dashboard_overview.call_args.kwargs["range_name"],
            "month",
        )

    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_get_dashboard_overview_rejects_invalid_range(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
    ) -> None:
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user

        response = self.client.get(
            "/api/v1/dashboard/overview?range=year",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 422)

    def test_get_dashboard_overview_requires_auth(self) -> None:
        response = self.client.get("/api/v1/dashboard/overview")

        self.assertEqual(response.status_code, 401)

    @patch("linkedin.api.routes.manager.get_manager_dashboard")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_get_manager_dashboard_returns_counts(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_get_manager_dashboard,
    ) -> None:
        manager = SimpleNamespace(id="manager-user-id", role="manager")
        mock_decode_jwt_token.return_value = {"sub": manager.id}
        mock_get_user_by_id.return_value = manager
        mock_get_manager_dashboard.return_value = {
            "totals": {
                "total_leads": 120,
                "calls_scheduled": 44,
                "qualified": 38,
                "pre_sale": 21,
                "not_a_fit": 17,
            },
            "users": [
                {
                    "user_id": "talha_user_id",
                    "name": "Talha",
                    "email": "talha@example.com",
                    "leads": {
                        "total_leads": 42,
                        "calls_scheduled": 15,
                        "qualified": 12,
                        "pre_sale": 7,
                        "not_a_fit": 5,
                    },
                },
                {
                    "user_id": "ali_user_id",
                    "name": "Ali",
                    "email": "ali@example.com",
                    "leads": {
                        "total_leads": 78,
                        "calls_scheduled": 29,
                        "qualified": 26,
                        "pre_sale": 14,
                        "not_a_fit": 12,
                    },
                },
            ],
        }

        response = self.client.get(
            "/api/v1/manager/dashboard",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["totals"]["total_leads"], 120)
        self.assertEqual(body["users"][0]["user_id"], "talha_user_id")
        mock_get_manager_dashboard.assert_called_once()

    @patch("linkedin.api.routes.manager.get_manager_dashboard")
    @patch("linkedin.api.deps.get_user_by_id")
    @patch("linkedin.api.deps.decode_jwt_token")
    def test_get_manager_dashboard_returns_403_for_regular_user(
        self,
        mock_decode_jwt_token,
        mock_get_user_by_id,
        mock_get_manager_dashboard,
    ) -> None:
        user = SimpleNamespace(id="regular-user-id", role="user")
        mock_decode_jwt_token.return_value = {"sub": user.id}
        mock_get_user_by_id.return_value = user
        mock_get_manager_dashboard.side_effect = ManagerPermissionError(
            "Manager access required."
        )

        response = self.client.get(
            "/api/v1/manager/dashboard",
            cookies={"access_token": "access-123"},
        )

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
