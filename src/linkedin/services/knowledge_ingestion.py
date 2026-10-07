from __future__ import annotations

import base64
import re
from io import BytesIO
from uuid import uuid4

from sqlalchemy.orm import Session

from linkedin.core.config import settings
from linkedin.integrations.minio import download_object_bytes
from linkedin.integrations.openai.embeddings import create_embeddings
from linkedin.integrations.openai.client import get_openai_client
from linkedin.integrations.qdrant import upsert_knowledge_vectors
from linkedin.repositories.knowledge_ingestion import (
    create_knowledge_chunks,
    get_project_file,
    mark_file_failed,
    mark_file_processing,
)


try:
    from docx import Document
except ImportError:
    Document = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


class PermanentIngestionError(ValueError):
    """Raised for jobs that should fail once instead of being retried."""


def _tokenize(text: str) -> list[str]:
    return text.split()


def _count_tokens(text: str) -> int:
    return len(_tokenize(text))


def _normalize_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n+", normalized)
        if paragraph.strip()
    ]


def _tail_tokens(text: str, token_count: int) -> str:
    if token_count <= 0:
        return ""
    tokens = _tokenize(text)
    return " ".join(tokens[-token_count:])


def chunk_text_by_paragraph(
    text: str,
    *,
    chunk_size_tokens: int = 800,
    chunk_overlap_tokens: int = 160,
) -> list[str]:
    paragraphs = _normalize_paragraphs(text)
    if not paragraphs:
        return []

    chunks: list[str] = []
    current_paragraphs: list[str] = []
    current_token_count = 0

    for paragraph in paragraphs:
        paragraph_token_count = _count_tokens(paragraph)
        if (
            current_paragraphs
            and current_token_count + paragraph_token_count > chunk_size_tokens
        ):
            chunk = "\n\n".join(current_paragraphs)
            chunks.append(chunk)
            overlap_text = _tail_tokens(chunk, chunk_overlap_tokens)
            current_paragraphs = [overlap_text] if overlap_text else []
            current_token_count = _count_tokens(overlap_text)

        current_paragraphs.append(paragraph)
        current_token_count += paragraph_token_count

    if current_paragraphs:
        chunks.append("\n\n".join(current_paragraphs))

    return chunks


def _extract_pdf_text(file_bytes: bytes) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed. Run `uv sync`.")

    reader = PdfReader(BytesIO(file_bytes))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _extract_docx_text(file_bytes: bytes) -> str:
    if Document is None:
        raise RuntimeError("python-docx is not installed. Run `uv sync`.")

    document = Document(BytesIO(file_bytes))
    return "\n\n".join(
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    )


def _extract_plain_text(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return file_bytes.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode text file.")


def _extract_image_text(file_bytes: bytes, content_type: str) -> str:
    encoded_image = base64.b64encode(file_bytes).decode("ascii")
    response = get_openai_client().responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Extract all readable text from this image. "
                            "Return only the extracted text. If there is no "
                            "readable text, return an empty response."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:{content_type};base64,{encoded_image}",
                    },
                ],
            }
        ],
    )
    return str(response.output_text).strip()


def extract_text_from_file(
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> str:
    normalized_content_type = content_type.lower()
    normalized_filename = filename.lower()

    if normalized_content_type == "application/pdf" or normalized_filename.endswith(".pdf"):
        return _extract_pdf_text(file_bytes)
    if (
        normalized_content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or normalized_filename.endswith(".docx")
    ):
        return _extract_docx_text(file_bytes)
    if (
        normalized_content_type.startswith("text/")
        or normalized_filename.endswith((".txt", ".md", ".csv"))
    ):
        return _extract_plain_text(file_bytes)
    if (
        normalized_content_type.startswith("image/")
        or normalized_filename.endswith((".png", ".jpg", ".jpeg", ".webp"))
    ):
        return _extract_image_text(file_bytes, normalized_content_type)

    raise PermanentIngestionError(f"Unsupported knowledge file type: {content_type}")


def _build_project_context_text(project_file) -> str:
    project = getattr(project_file, "project", None)
    if project is None:
        return ""

    context_parts = [f"Project name: {project.name}"]
    if project.description:
        context_parts.append(f"Project description: {project.description}")
    context_parts.append(f"File label: {project_file.label}")
    context_parts.append(f"Filename: {project_file.filename}")
    return "\n".join(context_parts)


def _compose_rag_training_text(*, project_file, extracted_text: str) -> str:
    project_context_text = _build_project_context_text(project_file)
    if not project_context_text:
        return extracted_text
    return f"{project_context_text}\n\n{extracted_text}".strip()


def _qdrant_payload_for_chunk(
    *,
    project_file,
    chunk_text: str,
    chunk_index: int,
    point_id: str,
) -> dict[str, str | int | None]:
    return {
        "chunk_id": point_id,
        "project_id": project_file.project_id,
        "project_file_id": project_file.id,
        "user_id": project_file.user_id,
        "label": project_file.label,
        "project_name": project_file.project.name,
        "project_description": project_file.project.description,
        "filename": project_file.filename,
        "content_type": project_file.content_type,
        "bucket": project_file.bucket,
        "object_key": project_file.object_key,
        "chunk_index": chunk_index,
        "status": "active",
        "text": chunk_text,
    }


def ingest_project_file(db: Session, *, project_file_id: str) -> None:
    project_file = get_project_file(db, project_file_id)
    if project_file is None:
        return

    try:
        mark_file_processing(db, project_file)
        file_bytes = download_object_bytes(
            bucket=project_file.bucket,
            object_key=project_file.object_key,
        )
        extracted_text = extract_text_from_file(
            file_bytes=file_bytes,
            filename=project_file.filename,
            content_type=project_file.content_type,
        )
        rag_training_text = _compose_rag_training_text(
            project_file=project_file,
            extracted_text=extracted_text,
        )
        chunk_texts = chunk_text_by_paragraph(
            rag_training_text,
            chunk_size_tokens=settings.knowledge_chunk_size_tokens,
            chunk_overlap_tokens=settings.knowledge_chunk_overlap_tokens,
        )
        if not chunk_texts:
            raise ValueError("No text could be extracted from the uploaded file.")

        vectors = create_embeddings(chunk_texts)
        point_ids = [str(uuid4()) for _ in chunk_texts]
        payloads = [
            _qdrant_payload_for_chunk(
                project_file=project_file,
                chunk_text=chunk_text,
                chunk_index=index,
                point_id=point_ids[index],
            )
            for index, chunk_text in enumerate(chunk_texts)
        ]
        upsert_knowledge_vectors(
            vectors=vectors,
            payloads=payloads,
            point_ids=point_ids,
        )
        create_knowledge_chunks(
            db,
            project_file=project_file,
            chunks=[
                {
                    "text": chunk_text,
                    "qdrant_point_id": point_ids[index],
                    "metadata": {
                        "embedding_model": settings.embedding_model,
                        "chunk_size_tokens": settings.knowledge_chunk_size_tokens,
                        "chunk_overlap_tokens": settings.knowledge_chunk_overlap_tokens,
                        "project_name": project_file.project.name,
                        "project_description": project_file.project.description,
                    },
                }
                for index, chunk_text in enumerate(chunk_texts)
            ],
        )
    except Exception as exc:
        mark_file_failed(db, project_file, error=str(exc))
        raise
