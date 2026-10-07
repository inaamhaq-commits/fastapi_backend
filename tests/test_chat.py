import unittest
from unittest.mock import Mock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from linkedin.core.enums import ActorTaskStatus
from linkedin.core.enums import JobStatus
from linkedin.main import app
from linkedin.schemas.chat import (
    ActorRawDocumentResponse,
    ChatJobDetailResponse,
    ChatJobResponse,
    ChatRequest,
    JobPostingResponse,
)
from linkedin.services.chat import create_chat_job


class ChatRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_create_chat_route_supports_cors_preflight(self) -> None:
        response = self.client.options(
            "/api/v1/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )

    @patch("linkedin.api.routes.chat.create_chat_job")
    def test_create_chat_route_returns_job_id(self, mock_create_chat_job) -> None:
        job_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_create_chat_job.return_value = ChatJobResponse(
            job_id=job_id,
            status="queued",
        )

        response = self.client.post(
            "/api/v1/chat",
            json={"message": "Hello, I need help with job search"},
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["job_id"], str(job_id))
        self.assertEqual(response.json()["status"], "queued")

    def test_create_chat_route_rejects_blank_message(self) -> None:
        response = self.client.post("/api/v1/chat", json={"message": "   "})

        self.assertEqual(response.status_code, 422)

    @patch("linkedin.api.routes.chat.get_chat_job_detail")
    def test_get_chat_job_status_returns_job(self, mock_get_chat_job_detail) -> None:
        job_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_get_chat_job_detail.return_value = ChatJobDetailResponse(
            id=job_id,
            user_message="hello",
            normalized_query=None,
            status=JobStatus.QUEUED,
            created_at="2026-08-17T00:00:00Z",
            updated_at="2026-08-17T00:00:00Z",
            error=None,
            actor_tasks=[],
            actor_runs=[],
        )

        response = self.client.get(f"/api/v1/jobs/{job_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(job_id))
        self.assertEqual(response.json()["status"], "queued")

    @patch("linkedin.api.routes.chat.get_chat_job_detail")
    def test_get_chat_job_status_returns_404_when_missing(
        self,
        mock_get_chat_job_detail,
    ) -> None:
        job_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_get_chat_job_detail.return_value = None

        response = self.client.get(f"/api/v1/jobs/{job_id}")

        self.assertEqual(response.status_code, 404)

    @patch("linkedin.api.routes.chat.get_chat_job_results")
    def test_get_chat_results_returns_list(self, mock_get_chat_job_results) -> None:
        job_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_get_chat_job_results.return_value = [
            JobPostingResponse(
                id=UUID("22345678-1234-5678-1234-567812345678"),
                job_id=job_id,
                actor_task_id=UUID("32345678-1234-5678-1234-567812345678"),
                actor_run_id=UUID("42345678-1234-5678-1234-567812345678"),
                source_actor_key="linkedin_jobs",
                external_id="ext-1",
                title="Python Engineer",
                company_name="Acme",
                description="Build APIs",
                job_type="full-time",
                location="Remote",
                job_url="https://example.com/job/1",
                company_page_url="https://example.com/company/acme",
                company_website_url="https://acme.com",
                company_website_domain="acme.com",
                linkedin_url="https://linkedin.com/jobs/view/1",
                posted_at=None,
                source_site="linkedin",
                created_at="2026-08-17T00:00:00Z",
                updated_at="2026-08-17T00:00:00Z",
            )
        ]

        response = self.client.get(f"/api/v1/jobs/{job_id}/results")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], "Python Engineer")

    @patch("linkedin.api.routes.chat.get_all_chat_results")
    def test_get_all_results_returns_list(self, mock_get_all_chat_results) -> None:
        job_id = UUID("12345678-1234-5678-1234-567812345678")
        mock_get_all_chat_results.return_value = [
            JobPostingResponse(
                id=UUID("22345678-1234-5678-1234-567812345678"),
                job_id=job_id,
                actor_task_id=UUID("32345678-1234-5678-1234-567812345678"),
                actor_run_id=UUID("42345678-1234-5678-1234-567812345678"),
                source_actor_key="glassdoor_jobs",
                external_id="ext-1",
                title="Python Engineer",
                company_name="Acme",
                description="Build APIs",
                job_type="full-time",
                location="Remote",
                job_url="https://example.com/job/1",
                company_page_url="https://example.com/company/acme",
                company_website_url="https://acme.com",
                company_website_domain="acme.com",
                linkedin_url="https://linkedin.com/jobs/view/1",
                posted_at=None,
                source_site="glassdoor",
                created_at="2026-08-17T00:00:00Z",
                updated_at="2026-08-17T00:00:00Z",
            )
        ]

        response = self.client.get("/api/v1/all")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], "Python Engineer")


class ChatServiceTests(unittest.TestCase):
    def test_create_chat_request_schema_accepts_message(self) -> None:
        payload = ChatRequest(message="Find product manager roles")

        self.assertEqual(payload.message, "Find product manager roles")

    @patch("linkedin.services.chat.create_actor_task_record")
    @patch("linkedin.services.chat.generate_actor_tasks")
    @patch("linkedin.services.chat.create_chat_job_record")
    def test_create_chat_job_creates_three_source_tasks(
        self,
        mock_create_chat_job_record,
        mock_generate_actor_tasks,
        mock_create_actor_task_record,
    ) -> None:
        db = Mock()
        chat_job = Mock()
        chat_job.id = UUID("12345678-1234-5678-1234-567812345678")
        chat_job.status = JobStatus.PLANNING.value
        mock_create_chat_job_record.return_value = chat_job

        mock_generate_actor_tasks.return_value = [
            Mock(
                normalized_query="software engineer remote",
                actor_key="glassdoor_jobs",
                actor_input={"keywords": "software engineer remote"},
            ),
            Mock(
                normalized_query="software engineer remote",
                actor_key="wellfound_jobs",
                actor_input={"query": "software engineer remote"},
            ),
            Mock(
                normalized_query="software engineer remote",
                actor_key="workable_jobs",
                actor_input={"keyword": "software engineer remote"},
            ),
        ]

        created_tasks = [
            Mock(id="glassdoor-task-id", actor_key="glassdoor_jobs"),
            Mock(id="wellfound-task-id", actor_key="wellfound_jobs"),
            Mock(id="workable-task-id", actor_key="workable_jobs"),
        ]
        mock_create_actor_task_record.side_effect = created_tasks

        response = create_chat_job(
            db,
            ChatRequest(message="Find remote software engineer jobs"),
        )

        self.assertEqual(str(response.job_id), "12345678-1234-5678-1234-567812345678")
        self.assertEqual(response.status, "queued")
        self.assertEqual(chat_job.normalized_query, "software engineer remote")
        self.assertEqual(chat_job.status, JobStatus.QUEUED.value)
        self.assertEqual(mock_create_actor_task_record.call_count, 3)

    @patch("linkedin.services.chat.create_actor_task_record")
    @patch("linkedin.services.chat.generate_actor_tasks")
    @patch("linkedin.services.chat.create_chat_job_record")
    def test_create_chat_job_marks_created_tasks_failed_on_task_error(
        self,
        mock_create_chat_job_record,
        mock_generate_actor_tasks,
        mock_create_actor_task_record,
    ) -> None:
        db = Mock()
        chat_job = Mock()
        chat_job.id = UUID("12345678-1234-5678-1234-567812345678")
        chat_job.status = JobStatus.PLANNING.value
        chat_job.error = None
        mock_create_chat_job_record.return_value = chat_job

        mock_generate_actor_tasks.return_value = [
            Mock(
                normalized_query="software engineer remote",
                actor_key="glassdoor_jobs",
                actor_input={"keywords": "software engineer remote"},
            ),
            Mock(
                normalized_query="software engineer remote",
                actor_key="wellfound_jobs",
                actor_input={"query": "software engineer remote"},
            ),
            Mock(
                normalized_query="software engineer remote",
                actor_key="workable_jobs",
                actor_input={"keyword": "software engineer remote"},
            ),
        ]

        first_task = Mock(id="glassdoor-task-id", actor_key="glassdoor_jobs")
        second_task = Mock(
            id="wellfound-task-id",
            actor_key="wellfound_jobs",
            status=ActorTaskStatus.QUEUED.value,
        )
        mock_create_actor_task_record.side_effect = [
            first_task,
            second_task,
            RuntimeError("task create failed"),
        ]

        with self.assertRaises(RuntimeError):
            create_chat_job(
                db,
                ChatRequest(message="Find remote software engineer jobs"),
            )

        self.assertEqual(chat_job.status, JobStatus.FAILED.value)
        self.assertEqual(chat_job.error, "task create failed")
        self.assertEqual(second_task.status, ActorTaskStatus.FAILED.value)
