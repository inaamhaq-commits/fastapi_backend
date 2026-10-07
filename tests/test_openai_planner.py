import unittest
from unittest.mock import Mock, patch

from linkedin.integrations.openai.planner import (
    generate_actor_tasks,
    generate_glassdoor_actor_task,
    generate_wellfound_actor_task,
    generate_workable_actor_task,
)


class OpenAIPlannerTests(unittest.TestCase):
    @patch("linkedin.integrations.openai.planner.get_openai_client")
    def test_generate_glassdoor_actor_task_returns_normalized_payload(
        self,
        mock_get_openai_client,
    ) -> None:
        client = mock_get_openai_client.return_value
        client.responses.create.return_value = Mock(
            output_text=(
                '{"normalized_query":"software engineer remote",'
                '"actor_key":"glassdoor_jobs",'
                '"actor_input":{"keywords":"software engineer remote",'
                '"location":"remote","daysOld":30,"easyApply":false,'
                '"remoteWorkType":true,"minRating":0,"radius":"25",'
                '"employerSizes":"","sortBy":"relevant_desc","limit":100,'
                '"urlParam":[],"excludeJobIds":[]}}'
            )
        )

        planned = generate_glassdoor_actor_task("Find remote software engineer jobs")

        self.assertEqual(planned.actor_key, "glassdoor_jobs")
        self.assertEqual(planned.normalized_query, "software engineer remote")
        self.assertEqual(planned.actor_input["keywords"], "software engineer remote")
        self.assertEqual(planned.actor_input["limit"], 100)

    @patch("linkedin.integrations.openai.planner.get_openai_client")
    def test_generate_actor_tasks_returns_three_sources(
        self,
        mock_get_openai_client,
    ) -> None:
        client = mock_get_openai_client.return_value
        client.responses.create.return_value = Mock(
            output_text=(
                '{"normalized_query":"software engineer remote",'
                '"actor_key":"glassdoor_jobs",'
                '"actor_input":{"keywords":"software engineer remote",'
                '"location":"remote","daysOld":30,"easyApply":false,'
                '"remoteWorkType":true,"minRating":0,"radius":"25",'
                '"employerSizes":"","sortBy":"relevant_desc","limit":100,'
                '"urlParam":[],"excludeJobIds":[]}}'
            )
        )

        planned_tasks = generate_actor_tasks("Find remote software engineer jobs")

        self.assertEqual(len(planned_tasks), 3)
        self.assertEqual(planned_tasks[0].actor_key, "glassdoor_jobs")
        self.assertEqual(planned_tasks[1].actor_key, "wellfound_jobs")
        self.assertEqual(planned_tasks[2].actor_key, "workable_jobs")
        self.assertEqual(planned_tasks[1].actor_input["query"], "software engineer remote")
        self.assertEqual(planned_tasks[2].actor_input["keyword"], "software engineer remote")

    @patch("linkedin.integrations.openai.planner.get_openai_client")
    def test_generate_wellfound_actor_task_derives_page_count(
        self,
        mock_get_openai_client,
    ) -> None:
        client = mock_get_openai_client.return_value
        client.responses.create.return_value = Mock(
            output_text=(
                '{"normalized_query":"backend engineer",'
                '"actor_key":"glassdoor_jobs",'
                '"actor_input":{"keywords":"backend engineer",'
                '"location":"united kingdom","daysOld":30,"easyApply":false,'
                '"remoteWorkType":false,"minRating":0,"radius":"25",'
                '"employerSizes":"","sortBy":"relevant_desc","limit":60,'
                '"urlParam":[],"excludeJobIds":[]}}'
            )
        )

        glassdoor_task = generate_glassdoor_actor_task("Find backend engineer jobs")
        wellfound_task = generate_wellfound_actor_task(glassdoor_task)

        self.assertEqual(wellfound_task.actor_key, "wellfound_jobs")
        self.assertEqual(wellfound_task.actor_input["query"], "backend engineer")
        self.assertFalse(wellfound_task.actor_input["remote"])
        self.assertEqual(wellfound_task.actor_input["maxResults"], 60)
        self.assertEqual(wellfound_task.actor_input["maxPages"], 3)

    @patch("linkedin.integrations.openai.planner.get_openai_client")
    def test_generate_workable_actor_task_uses_normalized_query_and_location(
        self,
        mock_get_openai_client,
    ) -> None:
        client = mock_get_openai_client.return_value
        client.responses.create.return_value = Mock(
            output_text=(
                '{"normalized_query":"product manager",'
                '"actor_key":"glassdoor_jobs",'
                '"actor_input":{"keywords":"product manager",'
                '"location":"Germany","daysOld":30,"easyApply":false,'
                '"remoteWorkType":false,"minRating":0,"radius":"25",'
                '"employerSizes":"","sortBy":"relevant_desc","limit":20,'
                '"urlParam":[],"excludeJobIds":[]}}'
            )
        )

        glassdoor_task = generate_glassdoor_actor_task("Find product manager jobs in Germany")
        workable_task = generate_workable_actor_task(glassdoor_task)

        self.assertEqual(workable_task.actor_key, "workable_jobs")
        self.assertEqual(workable_task.actor_input["keyword"], "product manager")
        self.assertEqual(workable_task.actor_input["location"], "Germany")
        self.assertEqual(workable_task.actor_input["results_wanted"], 20)
