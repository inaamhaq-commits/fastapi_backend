import unittest
from unittest.mock import Mock, patch

from redis.exceptions import TimeoutError as RedisTimeoutError

from linkedin.core.enums import ActorTaskStatus
from linkedin.workers.glassdoor_worker import (
    fetch_actor_items,
    map_posting_fields,
    pop_queue_message,
    process_actor_task,
)


class GlassdoorWorkerTests(unittest.TestCase):
    @patch("linkedin.workers.glassdoor_worker.get_redis_client")
    def test_pop_queue_message_returns_none_on_redis_timeout(
        self,
        mock_get_redis_client,
    ) -> None:
        redis_client = mock_get_redis_client.return_value
        redis_client.blpop.side_effect = RedisTimeoutError("timed out")

        message = pop_queue_message(block_seconds=1)

        self.assertIsNone(message)

    def test_map_posting_fields_extracts_expected_values(self) -> None:
        mapped = map_posting_fields(
            {
                "companyName": "Acme",
                "title": "Software Engineer",
                "description": "Build APIs",
                "jobType": "Full-time",
                "location": "Remote",
                "url": "https://example.com/jobs/1",
                "companyPageUrl": "https://example.com/company/acme",
                "companyWebsite": "https://acme.com/about",
                "linkedinUrl": "https://linkedin.com/jobs/view/1",
                "jobId": "ext-123",
            }
        )

        self.assertEqual(mapped["company_name"], "Acme")
        self.assertEqual(mapped["title"], "Software Engineer")
        self.assertEqual(mapped["external_id"], "ext-123")
        self.assertEqual(mapped["company_website_url"], "https://acme.com/about")
        self.assertEqual(mapped["company_website_domain"], "acme.com")

    @patch("linkedin.workers.glassdoor_worker.get_apify_client")
    def test_fetch_actor_items_supports_apify_run_object(
        self,
        mock_get_apify_client,
    ) -> None:
        actor_task = Mock()
        actor_task.actor_input_json = {"keywords": "Software Engineer"}

        run = Mock()
        run.id = "run-123"
        run.default_dataset_id = "dataset-456"

        client = mock_get_apify_client.return_value
        client.actor.return_value.call.return_value = run
        client.dataset.return_value.iterate_items.return_value = [
            {"title": "Software Engineer"}
        ]

        run_id, items = fetch_actor_items(actor_task)

        self.assertEqual(run_id, "run-123")
        self.assertEqual(items[0]["title"], "Software Engineer")

    @patch("linkedin.workers.glassdoor_worker.finalize_failure")
    @patch("linkedin.workers.glassdoor_worker.fetch_actor_items")
    @patch("linkedin.workers.glassdoor_worker.start_actor_run")
    @patch("linkedin.workers.glassdoor_worker.get_actor_task")
    @patch("linkedin.workers.glassdoor_worker.get_session_factory")
    def test_process_actor_task_rolls_back_before_finalize_failure(
        self,
        mock_get_session_factory,
        mock_get_actor_task,
        mock_start_actor_run,
        mock_fetch_actor_items,
        mock_finalize_failure,
    ) -> None:
        db = Mock()
        session_factory = Mock()
        session_factory.return_value.__enter__ = Mock(return_value=db)
        session_factory.return_value.__exit__ = Mock(return_value=False)
        mock_get_session_factory.return_value = session_factory

        actor_task = Mock()
        actor_task.id = "task-1"
        actor_task.status = ActorTaskStatus.QUEUED.value
        mock_get_actor_task.return_value = actor_task
        mock_start_actor_run.return_value = Mock()
        mock_fetch_actor_items.side_effect = RuntimeError("insert failed")

        process_actor_task("task-1")

        db.rollback.assert_called_once()
        mock_finalize_failure.assert_called_once()
