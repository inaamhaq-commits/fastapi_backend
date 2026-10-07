import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from linkedin.schemas.projects import ProjectCreateRequest
from linkedin.services.projects import create_knowledge_project, complete_project_upload


class ProjectServiceTests(unittest.TestCase):
    def test_create_knowledge_project_uses_filenames_as_labels(self) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        project = SimpleNamespace(id="87654321-4321-6789-4321-678987654321")
        files = [
            SimpleNamespace(
                id="11111111-1111-1111-1111-111111111111",
                filename="Healthcare Policy.pdf",
                label="healthcare-policy",
                content_type="application/pdf",
                bucket="knowledge-base",
                object_key="",
            ),
            SimpleNamespace(
                id="22222222-2222-2222-2222-222222222222",
                filename="Fintech FAQ.docx",
                label="fintech-faq",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                bucket="knowledge-base",
                object_key="",
            ),
        ]

        def create_file_side_effect(*args, **kwargs):
            return files.pop(0)

        payload = ProjectCreateRequest(
            name="Sales Assistant",
            description="Response knowledge",
            files=[
                {
                    "filename": "Healthcare Policy.pdf",
                    "content_type": "application/pdf",
                    "file_size": 100,
                },
                {
                    "filename": "Fintech FAQ.docx",
                    "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "file_size": 200,
                },
            ],
        )

        with (
            patch("linkedin.services.projects.create_project", return_value=project),
            patch(
                "linkedin.services.projects.create_project_file",
                side_effect=create_file_side_effect,
            ) as mock_create_file,
            patch(
                "linkedin.services.projects.create_presigned_put_url",
                side_effect=["https://minio/upload-1", "https://minio/upload-2"],
            ),
        ):
            response = create_knowledge_project(db, payload, user)

        self.assertEqual(response.status, "uploading")
        self.assertEqual(len(response.uploads), 2)
        self.assertEqual(response.uploads[0].label, "healthcare-policy")
        self.assertEqual(response.uploads[1].label, "fintech-faq")
        self.assertEqual(response.uploads[0].upload_url, "https://minio/upload-1")
        self.assertEqual(response.uploads[1].upload_url, "https://minio/upload-2")
        self.assertIn("Healthcare%20Policy.pdf", response.uploads[0].object_key)
        self.assertEqual(mock_create_file.call_args_list[0].kwargs["label"], "healthcare-policy")
        self.assertEqual(mock_create_file.call_args_list[1].kwargs["label"], "fintech-faq")
        db.commit.assert_called_once()

    @patch("linkedin.services.projects.mark_project_files_uploaded")
    @patch("linkedin.services.projects.get_project_for_user")
    def test_complete_project_upload_marks_files_uploaded_without_redis(
        self,
        mock_get_project_for_user,
        mock_mark_project_files_uploaded,
    ) -> None:
        db = Mock()
        user = SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
        project = SimpleNamespace(
            id="87654321-4321-6789-4321-678987654321",
            files=[
                SimpleNamespace(id="11111111-1111-1111-1111-111111111111"),
                SimpleNamespace(id="22222222-2222-2222-2222-222222222222"),
            ],
        )
        mock_get_project_for_user.return_value = project
        mock_mark_project_files_uploaded.return_value = project

        result = complete_project_upload(
            db,
            project_id="87654321-4321-6789-4321-678987654321",
            user=user,
        )

        self.assertIs(result, project)
        mock_mark_project_files_uploaded.assert_called_once_with(db, project)


if __name__ == "__main__":
    unittest.main()
