from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from linkedin.api.deps import get_current_user, get_db
from linkedin.db.models.user import User
from linkedin.schemas.projects import (
    ProjectCompleteResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectResponse,
)
from linkedin.services.projects import (
    complete_project_upload,
    create_knowledge_project,
    get_knowledge_project,
    list_knowledge_projects,
)


router = APIRouter(prefix="/projects")


@router.post(
    "",
    response_model=ProjectCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a knowledge project and upload URLs for its files",
)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectCreateResponse:
    return create_knowledge_project(db, payload, current_user)


@router.post(
    "/{project_id}/complete",
    response_model=ProjectCompleteResponse,
    summary="Mark project files uploaded and queue ingestion",
)
def complete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectCompleteResponse:
    project = complete_project_upload(
        db,
        project_id=str(project_id),
        user=current_user,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    return ProjectCompleteResponse(
        project_id=project.id,
        status=project.status,
        files=list(project.files),
    )


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List your knowledge projects",
)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    return [
        ProjectResponse.model_validate(project)
        for project in list_knowledge_projects(db, current_user)
    ]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a knowledge project",
)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = get_knowledge_project(db, project_id=str(project_id), user=current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ProjectResponse.model_validate(project)
