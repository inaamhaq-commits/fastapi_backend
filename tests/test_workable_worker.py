import unittest
from unittest.mock import Mock, patch

from redis.exceptions import TimeoutError as RedisTimeoutError

from linkedin.workers.workable_worker import (
    build_run_input,
    fetch_actor_items,
    format_apify_error,
    map_posting_fields,
    pop_queue_message,
)


class WorkableWorkerTests(unittest.TestCase):
    @patch("linkedin.workers.workable_worker.get_redis_client")
    def test_pop_queue_message_returns_none_on_redis_timeout(
        self,
        mock_get_redis_client,
    ) -> None:
        redis_client = mock_get_redis_client.return_value
        redis_client.blpop.side_effect = RedisTimeoutError("timed out")

        message = pop_queue_message(block_seconds=1)

        self.assertIsNone(message)

    def test_build_run_input_applies_defaults_and_overrides(self) -> None:
        actor_task = Mock()
        actor_task.actor_input_json = {
            "keyword": "software engineer",
            "location": "Germany",
            "results_wanted": "50",
            "proxyConfiguration": {"useApifyProxy": True},
        }

        run_input = build_run_input(actor_task)

        self.assertEqual(run_input["keyword"], "software engineer")
        self.assertEqual(run_input["location"], "Germany")
        self.assertEqual(run_input["results_wanted"], 50)
        self.assertEqual(run_input["posted_date"], "anytime")
        self.assertTrue(run_input["proxyConfiguration"]["useApifyProxy"])

    def test_map_posting_fields_extracts_expected_values(self) -> None:
        mapped = map_posting_fields(
            {
                "company": "Acme",
                "title": "Software Engineer",
                "description": "Build internal tools",
                "employmentType": "Full-time",
                "location": "Berlin",
                "url": "https://jobs.workable.com/view/123",
                "companyUrl": "https://jobs.workable.com/acme",
                "companyWebsite": "https://acme.com/about",
                "id": "wrk-123",
                "publishedAt": "2026-08-17T10:00:00Z",
            }
        )

        self.assertEqual(mapped["company_name"], "Acme")
        self.assertEqual(mapped["title"], "Software Engineer")
        self.assertEqual(mapped["external_id"], "wrk-123")
        self.assertEqual(mapped["company_website_domain"], "acme.com")
        self.assertEqual(mapped["posted_at"].isoformat(), "2026-08-17T10:00:00+00:00")

    @patch("linkedin.workers.workable_worker.get_apify_client")
    def test_fetch_actor_items_supports_apify_run_object(
        self,
        mock_get_apify_client,
    ) -> None:
        actor_task = Mock()
        actor_task.actor_input_json = {"keyword": "software engineer"}

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

    def test_format_apify_error_falls_back_to_string(self) -> None:
        self.assertEqual(format_apify_error(RuntimeError("boom")), "boom")
