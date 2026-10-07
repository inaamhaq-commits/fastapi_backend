from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from sqlalchemy.orm import Session

from linkedin.core.config import settings
from linkedin.db.models.knowledge_project import KnowledgeProject
from linkedin.db.models.user import User
from linkedin.integrations.minio import create_presigned_put_url
from linkedin.repositories.projects import (
    create_project,
    create_project_file,
    get_project_for_user,
    list_projects_for_user,
    mark_project_files_uploaded,
)
from linkedin.schemas.projects import ProjectCreateRequest, ProjectCreateResponse


def _label_from_filename(filename: str) -> str:
    stem = Path(filename).stem.strip().lower()
    label = "".join(character if character.isalnum() else "-" for character in stem)
    return "-".join(part for part in label.split("-") if part) or "knowledge"


def _object_key(
    *,
    user_id: str,
    project_id: str,
    project_file_id: str,
    filename: str,
) -> str:
    safe_filename = quote(filename, safe="")
    return f"users/{user_id}/projects/{project_id}/{project_file_id}-{safe_filename}"


def _presigned_upload_url(
    *,
    bucket: str,
    object_key: str,
    content_type: str,
) -> str:
    return create_presigned_put_url(
        bucket=bucket,
        object_key=object_key,
        content_type=content_type,
    )


def create_knowledge_project(
    db: Session,
    payload: ProjectCreateRequest,
    user: User,
) -> ProjectCreateResponse:
    project = create_project(
        db,
        user_id=user.id,
        name=payload.name,
        description=payload.description,
    )
    uploads = []
    for index, file_payload in enumerate(payload.files):
        label = _label_from_filename(file_payload.filename)
        project_file = create_project_file(
            db,
            project_id=project.id,
            user_id=user.id,
            filename=file_payload.filename,
            label=label,
            content_type=file_payload.content_type,
            file_size=file_payload.file_size,
            bucket=settings.minio_bucket_name,
            object_key=f"pending/{project.id}/{index}",
        )
        project_file.object_key = _object_key(
            user_id=user.id,
            project_id=project.id,
            project_file_id=project_file.id,
            filename=file_payload.filename,
        )
        uploads.append(
            {
                "project_file_id": project_file.id,
                "filename": project_file.filename,
                "label": project_file.label,
                "bucket": project_file.bucket,
                "object_key": project_file.object_key,
                "upload_url": _presigned_upload_url(
                    bucket=project_file.bucket,
                    object_key=project_file.object_key,
                    content_type=project_file.content_type,
                ),
                "expires_in": settings.minio_presigned_url_seconds,
            }
        )
    db.commit()

    return ProjectCreateResponse(
        project_id=project.id,
        status="uploading",
        uploads=uploads,
    )


def complete_project_upload(
    db: Session,
    *,
    project_id: str,
    user: User,
) -> KnowledgeProject | None:
    project = get_project_for_user(db, project_id=project_id, user_id=user.id)
    if project is None:
        return None

    project = mark_project_files_uploaded(db, project)
    # Redis queueing is disabled for the low-user deployment.
    # Knowledge files remain marked as uploaded and can be processed manually.
    return project


def get_knowledge_project(
    db: Session,
    *,
    project_id: str,
    user: User,
) -> KnowledgeProject | None:
    return get_project_for_user(db, project_id=project_id, user_id=user.id)


def list_knowledge_projects(db: Session, user: User) -> list[KnowledgeProject]:
    return list_projects_for_user(db, user_id=user.id)
