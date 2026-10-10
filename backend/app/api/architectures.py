from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.architecture import ArchitectureRepository
from app.repositories.project import ProjectRepository
from app.schemas.architecture import ArchitectureCreate, ArchitectureResponse, ArchitectureUpdate
from app.services.architecture import ArchitectureService

router = APIRouter(prefix='/projects/{project_id}/architecture', tags=['architecture'])


def get_architecture_service(db: Session = Depends(get_db)) -> ArchitectureService:
    return ArchitectureService(
        ArchitectureRepository(db),
        ProjectRepository(db),
    )


@router.post('', response_model=ArchitectureResponse, status_code=status.HTTP_201_CREATED, summary='Create a project architecture')
def create_architecture(
    project_id: str,
    architecture_data: ArchitectureCreate,
    service: ArchitectureService = Depends(get_architecture_service),
) -> ArchitectureResponse:
    architecture = service.create_architecture(project_id, architecture_data)
    return ArchitectureResponse.model_validate(architecture)


@router.get('', response_model=ArchitectureResponse, summary='Get project architecture')
def get_architecture(
    project_id: str,
    service: ArchitectureService = Depends(get_architecture_service),
) -> ArchitectureResponse:
    architecture = service.get_architecture_by_project(project_id)
    return ArchitectureResponse.model_validate(architecture)


@router.patch('', response_model=ArchitectureResponse, summary='Update project architecture')
def update_architecture(
    project_id: str,
    architecture_data: ArchitectureUpdate,
    service: ArchitectureService = Depends(get_architecture_service),
) -> ArchitectureResponse:
    architecture = service.update_architecture_by_project(project_id, architecture_data)
    return ArchitectureResponse.model_validate(architecture)


@router.delete('', status_code=status.HTTP_204_NO_CONTENT, summary='Delete project architecture')
def delete_architecture(
    project_id: str,
    service: ArchitectureService = Depends(get_architecture_service),
) -> Response:
    service.delete_architecture_by_project(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ['router']
