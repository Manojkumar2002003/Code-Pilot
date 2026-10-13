from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.repositories.task import TaskRepository
from app.schemas.requirement import (
    RequirementCreate,
    RequirementResponse,
    RequirementUpdate,
    TaskAssociationRequest,
)
from app.schemas.task import TaskResponse
from app.services.requirement import RequirementService

router = APIRouter(prefix='/projects/{project_id}/requirements', tags=['requirements'])


def get_requirement_service(db: Session = Depends(get_db)) -> RequirementService:
    return RequirementService(
        RequirementRepository(db),
        ProjectRepository(db),
        TaskRepository(db),
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


@router.get('/{requirement_id}/tasks', response_model=list[TaskResponse], summary='List tasks associated with a requirement')
def list_requirement_tasks(
    project_id: str,
    requirement_id: str,
    service: RequirementService = Depends(get_requirement_service),
) -> list[TaskResponse]:
    tasks = service.list_tasks_for_requirement(project_id, requirement_id)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.post('/{requirement_id}/tasks', response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary='Link a task to a requirement')
def link_task_to_requirement(
    project_id: str,
    requirement_id: str,
    link_data: TaskAssociationRequest,
    service: RequirementService = Depends(get_requirement_service),
) -> TaskResponse:
    task = service.link_task(project_id, requirement_id, link_data.task_id)
    return TaskResponse.model_validate(task)


@router.post('/{requirement_id}/tasks/{task_id}', response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary='Link a task to a requirement by path')
def link_task_to_requirement_by_path(
    project_id: str,
    requirement_id: str,
    task_id: str,
    service: RequirementService = Depends(get_requirement_service),
) -> TaskResponse:
    task = service.link_task(project_id, requirement_id, task_id)
    return TaskResponse.model_validate(task)


@router.delete('/{requirement_id}/tasks/{task_id}', status_code=status.HTTP_204_NO_CONTENT, summary='Unlink a task from a requirement')
def unlink_task_from_requirement(
    project_id: str,
    requirement_id: str,
    task_id: str,
    service: RequirementService = Depends(get_requirement_service),
) -> Response:
    service.unlink_task(project_id, requirement_id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ['router']

