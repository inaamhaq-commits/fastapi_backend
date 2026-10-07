import unittest
from unittest.mock import patch

from linkedin.workers.runner import run_all_workers


class WorkerRunnerTests(unittest.TestCase):
    @patch("linkedin.workers.runner._start_worker_process")
    def test_run_all_workers_starts_all_workers(self, mock_start_worker_process) -> None:
        glassdoor_process = unittest.mock.Mock()
        wellfound_process = unittest.mock.Mock()
        workable_process = unittest.mock.Mock()
        mock_start_worker_process.side_effect = [
            glassdoor_process,
            wellfound_process,
            workable_process,
        ]

        run_all_workers()

        self.assertEqual(mock_start_worker_process.call_count, 3)
        glassdoor_process.join.assert_called_once()
        wellfound_process.join.assert_called_once()
        workable_process.join.assert_called_once()
