from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.requirement import RequirementCreate, RequirementResponse, RequirementUpdate
from app.services.requirement import RequirementService

router = APIRouter(prefix='/projects/{project_id}/requirements', tags=['requirements'])


def get_requirement_service(project_id: str, db: Session = Depends(get_db)) -> RequirementService:
    return RequirementService(
        RequirementRepository(db),
        ProjectRepository(db),
    )


@router.post('', response_model=RequirementResponse, status_code=status.HTTP_201_CREATED, summary='Create a requirement')
def create_requirement(project_id: str, requirement_data: RequirementCreate, service: RequirementService = Depends(get_requirement_service)) -> RequirementResponse:
    requirement = service.create_requirement(project_id, requirement_data)
    return RequirementResponse.model_validate(requirement)


@router.get('', response_model=list[RequirementResponse], summary='List requirements for a project')
def list_requirements(project_id: str, service: RequirementService = Depends(get_requirement_service)) -> list[RequirementResponse]:
    requirements = service.list_requirements(project_id)
    return [RequirementResponse.model_validate(requirement) for requirement in requirements]


@router.get('/{requirement_id}', response_model=RequirementResponse, summary='Get a requirement in a project context')
def get_requirement(project_id: str, requirement_id: str, service: RequirementService = Depends(get_requirement_service)) -> RequirementResponse:
    requirement = service.get_requirement(project_id, requirement_id)
    return RequirementResponse.model_validate(requirement)


@router.patch('/{requirement_id}', response_model=RequirementResponse, summary='Update a requirement')
def update_requirement(project_id: str, requirement_id: str, requirement_data: RequirementUpdate, service: RequirementService = Depends(get_requirement_service)) -> RequirementResponse:
    requirement = service.update_requirement(project_id, requirement_id, requirement_data)
    return RequirementResponse.model_validate(requirement)


@router.delete('/{requirement_id}', status_code=status.HTTP_204_NO_CONTENT, summary='Delete a requirement')
def delete_requirement(project_id: str, requirement_id: str, service: RequirementService = Depends(get_requirement_service)) -> Response:
    service.delete_requirement(project_id, requirement_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ['router']
