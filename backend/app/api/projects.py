from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project import ProjectService

router = APIRouter(prefix='/projects', tags=['projects'])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    repository = ProjectRepository(db)
    return ProjectService(repository)


@router.post('', response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_data: ProjectCreate, service: ProjectService = Depends(get_project_service)) -> ProjectResponse:
    project = service.create_project(project_data)
    return ProjectResponse.model_validate(project)


@router.get('', response_model=list[ProjectResponse])
def list_projects(service: ProjectService = Depends(get_project_service)) -> list[ProjectResponse]:
    projects = service.list_projects()
    return [ProjectResponse.model_validate(project) for project in projects]


@router.get('/{project_id}', response_model=ProjectResponse)
def get_project(project_id: str, service: ProjectService = Depends(get_project_service)) -> ProjectResponse:
    project = service.get_project(project_id)
    return ProjectResponse.model_validate(project)


@router.patch('/{project_id}', response_model=ProjectResponse)
def update_project(project_id: str, project_data: ProjectUpdate, service: ProjectService = Depends(get_project_service)) -> ProjectResponse:
    project = service.update_project(project_id, project_data)
    return ProjectResponse.model_validate(project)


@router.delete('/{project_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, service: ProjectService = Depends(get_project_service)) -> Response:
    service.delete_project(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
