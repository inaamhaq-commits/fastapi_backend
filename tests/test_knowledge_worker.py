import json
import unittest
from unittest.mock import Mock, patch

from openai import AuthenticationError

from linkedin.knowledge_worker_entrypoint import (
    _requeue_dead_letter_jobs,
    process_next_job,
)


class KnowledgeWorkerTests(unittest.TestCase):
    @patch("linkedin.knowledge_worker_entrypoint.get_session_factory")
    @patch("linkedin.knowledge_worker_entrypoint.ingest_project_file")
    def test_authentication_error_goes_to_dead_letter_without_retry(
        self,
        mock_ingest_project_file,
        mock_get_session_factory,
    ) -> None:
        redis_client = Mock()
        raw_payload = json.dumps({"project_file_id": "file-id"})
        redis_client.brpoplpush.return_value = raw_payload
        db = Mock()
        mock_get_session_factory.return_value.return_value.__enter__.return_value = db
        mock_ingest_project_file.side_effect = AuthenticationError(
            message="Incorrect API key provided.",
            response=Mock(status_code=401),
            body=None,
        )

        processed = process_next_job(redis_client)

        self.assertTrue(processed)
        redis_client.lrem.assert_called_once()
        redis_client.rpush.assert_called_once()
        self.assertEqual(
            redis_client.rpush.call_args.args[0],
            "queue:knowledge-ingestion:dead-letter",
        )

    def test_requeue_dead_letter_jobs_resets_attempt_count(self) -> None:
        redis_client = Mock()
        redis_client.lpop.side_effect = [
            json.dumps(
                {
                    "project_file_id": "file-id",
                    "attempt_count": 3,
                    "last_error": "old error",
                }
            ),
            None,
        ]

        requeued_count = _requeue_dead_letter_jobs(redis_client)

        self.assertEqual(requeued_count, 1)
        redis_client.rpush.assert_called_once()
        self.assertEqual(
            redis_client.rpush.call_args.args[0],
            "queue:knowledge-ingestion",
        )
        payload = json.loads(redis_client.rpush.call_args.args[1])
        self.assertEqual(payload["project_file_id"], "file-id")
        self.assertEqual(payload["attempt_count"], 0)
        self.assertNotIn("last_error", payload)


if __name__ == "__main__":
    unittest.main()
