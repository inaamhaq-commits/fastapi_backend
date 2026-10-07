from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from linkedin.core.enums import (
    KnowledgeFileProcessingStatus,
    KnowledgeFileUploadStatus,
    KnowledgeProjectStatus,
)
from linkedin.db.models.knowledge_project import KnowledgeProject
from linkedin.db.models.knowledge_project_file import KnowledgeProjectFile


def create_project(
    db: Session,
    *,
    user_id: str,
    name: str,
    description: str | None,
) -> KnowledgeProject:
    project = KnowledgeProject(
        user_id=user_id,
        name=name,
        description=description,
        status=KnowledgeProjectStatus.UPLOADING.value,
    )
    db.add(project)
    db.flush()
    return project


def create_project_file(
    db: Session,
    *,
    project_id: str,
    user_id: str,
    filename: str,
    label: str,
    content_type: str,
    file_size: int | None,
    bucket: str,
    object_key: str,
) -> KnowledgeProjectFile:
    project_file = KnowledgeProjectFile(
        project_id=project_id,
        user_id=user_id,
        filename=filename,
        label=label,
        content_type=content_type,
        file_size=file_size,
        bucket=bucket,
        object_key=object_key,
        upload_status=KnowledgeFileUploadStatus.PENDING.value,
        processing_status=KnowledgeFileProcessingStatus.QUEUED.value,
    )
    db.add(project_file)
    db.flush()
    return project_file


def get_project_for_user(
    db: Session,
    *,
    project_id: str,
    user_id: str,
) -> KnowledgeProject | None:
    statement = (
        select(KnowledgeProject)
        .options(selectinload(KnowledgeProject.files))
        .where(
            KnowledgeProject.id == project_id,
            KnowledgeProject.user_id == user_id,
        )
    )
    return db.scalars(statement).first()


def list_projects_for_user(db: Session, *, user_id: str) -> list[KnowledgeProject]:
    statement = (
        select(KnowledgeProject)
        .options(selectinload(KnowledgeProject.files))
        .where(KnowledgeProject.user_id == user_id)
        .order_by(KnowledgeProject.created_at.desc())
    )
    return list(db.scalars(statement).all())


def mark_project_files_uploaded(db: Session, project: KnowledgeProject) -> KnowledgeProject:
    project.status = KnowledgeProjectStatus.PROCESSING.value
    for project_file in project.files:
        project_file.upload_status = KnowledgeFileUploadStatus.UPLOADED.value
        project_file.processing_status = KnowledgeFileProcessingStatus.QUEUED.value
    db.commit()
    db.refresh(project)
    return project
