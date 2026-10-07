from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from linkedin.core.config import settings
from linkedin.core.enums import (
    KnowledgeFileProcessingStatus,
    KnowledgeProjectStatus,
)
from linkedin.db.models.knowledge_chunk import KnowledgeChunk
from linkedin.db.models.knowledge_project import KnowledgeProject
from linkedin.db.models.knowledge_project_file import KnowledgeProjectFile


def get_project_file(db: Session, project_file_id: str) -> KnowledgeProjectFile | None:
    statement = (
        select(KnowledgeProjectFile)
        .options(selectinload(KnowledgeProjectFile.project))
        .where(KnowledgeProjectFile.id == project_file_id)
    )
    return db.scalars(statement).first()


def mark_file_processing(db: Session, project_file: KnowledgeProjectFile) -> None:
    project_file.processing_status = KnowledgeFileProcessingStatus.PROCESSING.value
    db.commit()


def mark_file_failed(
    db: Session,
    project_file: KnowledgeProjectFile,
    *,
    error: str,
) -> None:
    project_file.processing_status = KnowledgeFileProcessingStatus.FAILED.value
    project_file.error = error
    db.commit()
    refresh_project_status(db, project_file.project_id)


def create_knowledge_chunks(
    db: Session,
    *,
    project_file: KnowledgeProjectFile,
    chunks: list[dict[str, Any]],
) -> list[KnowledgeChunk]:
    db.execute(
        delete(KnowledgeChunk).where(
            KnowledgeChunk.project_file_id == project_file.id,
        )
    )
    created_chunks = []
    for index, chunk_payload in enumerate(chunks):
        chunk_text = str(chunk_payload["text"])
        chunk = KnowledgeChunk(
            project_id=project_file.project_id,
            project_file_id=project_file.id,
            user_id=project_file.user_id,
            label=project_file.label,
            chunk_text=chunk_text,
            chunk_index=index,
            token_count=len(chunk_text.split()),
            qdrant_collection=settings.qdrant_collection_name,
            qdrant_point_id=str(chunk_payload["qdrant_point_id"]),
            chunk_metadata={
                "filename": project_file.filename,
                "content_type": project_file.content_type,
                "bucket": project_file.bucket,
                "object_key": project_file.object_key,
                **dict(chunk_payload.get("metadata", {})),
            },
        )
        db.add(chunk)
        created_chunks.append(chunk)

    project_file.processing_status = KnowledgeFileProcessingStatus.COMPLETED.value
    project_file.error = None
    db.commit()
    for chunk in created_chunks:
        db.refresh(chunk)
    refresh_project_status(db, project_file.project_id)
    return created_chunks


def refresh_project_status(db: Session, project_id: str) -> None:
    project = db.get(KnowledgeProject, project_id)
    if project is None:
        return

    files = list(project.files)
    if not files:
        project.status = KnowledgeProjectStatus.FAILED.value
        project.error = "Project has no files."
        db.commit()
        return

    statuses = {project_file.processing_status for project_file in files}
    if statuses == {KnowledgeFileProcessingStatus.COMPLETED.value}:
        project.status = KnowledgeProjectStatus.ACTIVE.value
        project.error = None
    elif KnowledgeFileProcessingStatus.FAILED.value in statuses and any(
        status == KnowledgeFileProcessingStatus.COMPLETED.value
        for status in statuses
    ):
        project.status = KnowledgeProjectStatus.PARTIAL_FAILED.value
    elif statuses == {KnowledgeFileProcessingStatus.FAILED.value}:
        project.status = KnowledgeProjectStatus.FAILED.value
        project.error = "All project files failed ingestion."
    else:
        project.status = KnowledgeProjectStatus.PROCESSING.value
    db.commit()
