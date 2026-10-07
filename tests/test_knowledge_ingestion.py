import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from linkedin.services.knowledge_ingestion import (
    PermanentIngestionError,
    _compose_rag_training_text,
    chunk_text_by_paragraph,
    extract_text_from_file,
    ingest_project_file,
)


class KnowledgeChunkingTests(unittest.TestCase):
    def test_chunk_text_by_paragraph_uses_configured_overlap(self) -> None:
        text = "\n\n".join(
            [
                " ".join(f"p{paragraph_index}w{word_index}" for word_index in range(100))
                for paragraph_index in range(10)
            ]
        )

        chunks = chunk_text_by_paragraph(
            text,
            chunk_size_tokens=800,
            chunk_overlap_tokens=160,
        )

        self.assertEqual(len(chunks), 2)
        self.assertLessEqual(len(chunks[0].split()), 800)
        self.assertEqual(chunks[0].split()[-160:], chunks[1].split()[:160])

    def test_chunk_text_by_paragraph_ignores_empty_paragraphs(self) -> None:
        chunks = chunk_text_by_paragraph(
            "First paragraph.\n\n\n   \n\nSecond paragraph.",
            chunk_size_tokens=800,
            chunk_overlap_tokens=160,
        )

        self.assertEqual(chunks, ["First paragraph.\n\nSecond paragraph."])

    def test_extract_text_from_file_supports_plain_text(self) -> None:
        text = extract_text_from_file(
            file_bytes=b"First paragraph.\n\nSecond paragraph.",
            filename="notes.txt",
            content_type="text/plain",
        )

        self.assertEqual(text, "First paragraph.\n\nSecond paragraph.")

    @patch("linkedin.services.knowledge_ingestion.get_openai_client")
    def test_extract_text_from_file_supports_images_with_vision_ocr(
        self,
        mock_get_openai_client,
    ) -> None:
        mock_get_openai_client.return_value.responses.create.return_value = (
            SimpleNamespace(output_text="Image text")
        )

        text = extract_text_from_file(
            file_bytes=b"image-bytes",
            filename="screenshot.png",
            content_type="image/png",
        )

        self.assertEqual(text, "Image text")

    def test_extract_text_from_file_raises_permanent_error_for_unknown_type(self) -> None:
        with self.assertRaises(PermanentIngestionError):
            extract_text_from_file(
                file_bytes=b"data",
                filename="archive.zip",
                content_type="application/zip",
            )

    def test_compose_rag_training_text_includes_project_description(self) -> None:
        project_file = SimpleNamespace(
            label="healthcare-policy",
            filename="policy.pdf",
            project=SimpleNamespace(
                name="Healthcare Project",
                description="Use this for healthcare compliance replies.",
            ),
        )

        text = _compose_rag_training_text(
            project_file=project_file,
            extracted_text="Document body.",
        )

        self.assertIn("Project name: Healthcare Project", text)
        self.assertIn(
            "Project description: Use this for healthcare compliance replies.",
            text,
        )
        self.assertIn("File label: healthcare-policy", text)
        self.assertTrue(text.endswith("Document body."))

    @patch("linkedin.services.knowledge_ingestion.create_knowledge_chunks")
    @patch("linkedin.services.knowledge_ingestion.upsert_knowledge_vectors")
    @patch("linkedin.services.knowledge_ingestion.create_embeddings")
    @patch("linkedin.services.knowledge_ingestion.download_object_bytes")
    @patch("linkedin.services.knowledge_ingestion.mark_file_processing")
    @patch("linkedin.services.knowledge_ingestion.get_project_file")
    def test_ingest_project_file_downloads_embeds_upserts_and_saves_chunks(
        self,
        mock_get_project_file,
        mock_mark_file_processing,
        mock_download_object_bytes,
        mock_create_embeddings,
        mock_upsert_knowledge_vectors,
        mock_create_knowledge_chunks,
    ) -> None:
        db = Mock()
        project_file = SimpleNamespace(
            id="file-id",
            project_id="project-id",
            user_id="user-id",
            label="handbook",
            filename="handbook.txt",
            content_type="text/plain",
            bucket="knowledge-base",
            object_key="users/user-id/projects/project-id/file-id-handbook.txt",
            project=SimpleNamespace(
                name="Handbook Project",
                description="Use this for onboarding answers.",
            ),
        )
        mock_get_project_file.return_value = project_file
        mock_download_object_bytes.return_value = b"Paragraph one.\n\nParagraph two."
        mock_create_embeddings.return_value = [[0.1, 0.2, 0.3]]

        ingest_project_file(db, project_file_id="file-id")

        mock_mark_file_processing.assert_called_once_with(db, project_file)
        mock_download_object_bytes.assert_called_once_with(
            bucket="knowledge-base",
            object_key="users/user-id/projects/project-id/file-id-handbook.txt",
        )
        mock_create_embeddings.assert_called_once_with(
            [
                "Project name: Handbook Project\n"
                "Project description: Use this for onboarding answers.\n"
                "File label: handbook\n"
                "Filename: handbook.txt\n\n"
                "Paragraph one.\n\nParagraph two."
            ]
        )
        mock_upsert_knowledge_vectors.assert_called_once()
        mock_create_knowledge_chunks.assert_called_once()
        saved_chunks = mock_create_knowledge_chunks.call_args.kwargs["chunks"]
        self.assertIn("Project name: Handbook Project", saved_chunks[0]["text"])
        self.assertIn(
            "Project description: Use this for onboarding answers.",
            saved_chunks[0]["text"],
        )
        self.assertIn("Paragraph one.\n\nParagraph two.", saved_chunks[0]["text"])
        self.assertIn("qdrant_point_id", saved_chunks[0])


if __name__ == "__main__":
    unittest.main()
